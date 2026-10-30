"""Narrow, workspace-confined project tools."""
import os
from pathlib import Path
import re
import subprocess
import sys

EXCLUDED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
PRIVATE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
MAX_FILE_BYTES = 200_000
MAX_WRITE_FILES = 50
MAX_WRITE_BYTES = 1_000_000


def _root() -> Path:
    root = Path(os.getenv("APOORVA_WORKSPACE", os.getcwd())).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("APOORVA_WORKSPACE must point to an existing directory")
    return root


def _is_safe_file(root: Path, path: Path) -> bool:
    if path.is_symlink() or path.name.startswith(".") or path.suffix.lower() in PRIVATE_SUFFIXES:
        return False
    lowered = path.name.lower()
    if any(secret in lowered for secret in ("secret", "credential", "token")):
        return False
    try:
        resolved = path.resolve()
        return root == resolved or root in resolved.parents
    except OSError:
        return False


def _target(relative_path: str) -> Path:
    root = _root()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Path is outside the configured workspace")
    return target


def list_project_files(limit: int = 200) -> dict:
    if not 1 <= limit <= 500:
        return {"success": False, "error": "limit must be between 1 and 500"}
    root, files = _root(), []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith(".") and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.is_file() and _is_safe_file(root, path):
                files.append(path.relative_to(root).as_posix())
                if len(files) >= limit:
                    return {"success": True, "workspace": str(root), "files": files, "truncated": True}
    return {"success": True, "workspace": str(root), "files": files, "truncated": False}


def read_project_file(path: str) -> dict:
    root, target = _root(), _target(path)
    if not target.is_file() or not _is_safe_file(root, target):
        return {"success": False, "error": "File does not exist or is excluded for safety"}
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        return {"success": False, "error": f"File exceeds the {MAX_FILE_BYTES}-byte read limit", "size_bytes": size}
    try:
        return {"success": True, "path": target.relative_to(root).as_posix(), "content": target.read_text(encoding="utf-8")}
    except UnicodeDecodeError:
        return {"success": False, "error": "File is not UTF-8 text"}


def search_project(pattern: str, limit: int = 100) -> dict:
    if not 1 <= limit <= 500 or len(pattern) > 300:
        return {"success": False, "error": "pattern must be at most 300 characters and limit between 1 and 500"}
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return {"success": False, "error": f"Invalid regular expression: {exc}"}
    root, matches = _root(), []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in EXCLUDED and not d.startswith(".") and not (Path(current) / d).is_symlink()]
        for name in names:
            path = Path(current) / name
            try:
                if not _is_safe_file(root, path) or path.stat().st_size > MAX_FILE_BYTES:
                    continue
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if regex.search(line):
                        matches.append({"path": path.relative_to(root).as_posix(), "line": number, "text": line[:500]})
                        if len(matches) >= limit:
                            return {"success": True, "matches": matches, "truncated": True}
            except (OSError, UnicodeError):
                continue
    return {"success": True, "matches": matches, "truncated": False}


def write_project_files(files: list[dict], overwrite: bool = False) -> dict:
    """Write a bounded batch of text files inside the configured workspace."""
    if not isinstance(files, list) or not files or len(files) > MAX_WRITE_FILES:
        return {"success": False, "error": f"Provide between 1 and {MAX_WRITE_FILES} files."}
    if not isinstance(overwrite, bool):
        return {"success": False, "error": "overwrite must be true or false."}

    root = _root()
    prepared = []
    total_bytes = 0
    seen = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "content"}:
            return {"success": False, "error": "Each file must contain only path and content."}
        relative = entry["path"]
        content = entry["content"]
        if not isinstance(relative, str) or not relative.strip() or not isinstance(content, str):
            return {"success": False, "error": "File paths and contents must be text."}
        lexical = Path(relative)
        if lexical.is_absolute() or ".." in lexical.parts:
            return {"success": False, "error": "Use a relative path inside the configured workspace."}
        target = _target(relative)
        normalized = target.relative_to(root).as_posix()
        if normalized in seen:
            return {"success": False, "error": f"Duplicate output path: {normalized}"}
        seen.add(normalized)
        if target.suffix.lower() in PRIVATE_SUFFIXES or target.name.startswith("."):
            return {"success": False, "error": f"Writing hidden or private file types is not allowed: {normalized}"}
        if any(part in EXCLUDED or part.startswith(".") for part in target.relative_to(root).parts[:-1]):
            return {"success": False, "error": f"Writing into hidden or excluded directories is not allowed: {normalized}"}
        cursor = root
        for part in lexical.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                return {"success": False, "error": f"Symbolic links are not allowed: {normalized}"}
        if target.exists() and not overwrite:
            return {"success": False, "error": f"File already exists; set overwrite=true to replace it: {normalized}"}
        encoded = content.encode("utf-8")
        total_bytes += len(encoded)
        if total_bytes > MAX_WRITE_BYTES:
            return {"success": False, "error": f"The batch exceeds the {MAX_WRITE_BYTES}-byte total limit."}
        prepared.append((target, normalized, encoded))

    # Validate the whole batch before changing anything; stage each file next to
    # its destination so replacement stays on the same filesystem.
    staged = []
    try:
        for target, normalized, encoded in prepared:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".apoorva-tmp")
            if temp.exists() or temp.is_symlink():
                raise FileExistsError(f"Temporary output already exists: {normalized}")
            temp.write_bytes(encoded)
            staged.append((temp, target, normalized))
        for temp, target, normalized in staged:
            if target.exists() and not overwrite:
                raise FileExistsError(f"File appeared during write: {normalized}")
            temp.replace(target)
    except Exception as exc:
        for temp, _, _ in staged:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        return {"success": False, "error": f"Could not write project files: {type(exc).__name__}: {exc}"}
    return {"success": True, "files_written": [relative for _, relative, _ in prepared], "total_bytes": total_bytes}


CHECKS = {
    "pytest": [sys.executable, "-m", "pytest", "-q"],
    "unittest": [sys.executable, "-m", "unittest", "discover", "-v"],
    "ruff": [sys.executable, "-m", "ruff", "check", "."],
}


def run_project_check(check: str, timeout_seconds: int = 300) -> dict:
    command = CHECKS.get(check)
    if command is None:
        return {"success": False, "error": f"Unsupported check. Choose: {', '.join(CHECKS)}"}
    if not 1 <= timeout_seconds <= 600:
        return {"success": False, "error": "timeout_seconds must be between 1 and 600"}
    try:
        result = subprocess.run(command, cwd=_root(), capture_output=True, text=True, timeout=timeout_seconds, shell=False, check=False)
        return {"success": result.returncode == 0, "check": check, "exit_code": result.returncode,
                "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:], "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"success": False, "check": check, "error": "Check timed out", "timed_out": True,
                "stdout": str(exc.stdout or "")[-12000:], "stderr": str(exc.stderr or "")[-12000:]}
