"""Download official sherpa-onnx English streaming ASR and Piper TTS models."""
import os
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "models" / "audio"
ARCHIVES = {
    "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17": (
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
        "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2"
    ),
    "vits-piper-en_US-lessac-medium": (
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"
        "vits-piper-en_US-lessac-medium.tar.bz2"
    ),
}
MAX_ARCHIVE_BYTES = 700 * 1024 * 1024
MAX_UNPACKED_BYTES = 900 * 1024 * 1024


def _extract_safely(archive_path: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with tarfile.open(archive_path, "r:bz2") as archive:
        members = archive.getmembers()
        total_size = sum(member.size for member in members)
        if total_size > MAX_UNPACKED_BYTES:
            raise ValueError("Model archive exceeds the configured extraction limit")
        for member in members:
            destination = (target / member.name).resolve()
            if destination != root and root not in destination.parents:
                raise ValueError("Unsafe path found in model archive")
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError("Links and device files are not allowed in model archives")
        archive.extractall(target, members=members)


def _download(url: str, archive_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Apoorva-local-voice-setup/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        length = int(response.headers.get("Content-Length", "0"))
        if length > MAX_ARCHIVE_BYTES:
            raise ValueError("Model archive exceeds the configured download limit")
        downloaded = 0
        with archive_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_ARCHIVE_BYTES:
                    raise ValueError("Model archive exceeds the configured download limit")
                output.write(chunk)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in ARCHIVES.items():
        target = DEST / name
        if target.is_dir() and any(target.iterdir()):
            print(f"Already present: {target}")
            continue
        archive_path = DEST / f"{name}.tar.bz2.part"
        final_archive = DEST / f"{name}.tar.bz2"
        print(f"Downloading {name} (free, local model; no API usage quota)...")
        try:
            _download(url, archive_path)
            os.replace(archive_path, final_archive)
            _extract_safely(final_archive, DEST)
            final_archive.unlink()
            print(f"Installed: {target}")
        except Exception:
            archive_path.unlink(missing_ok=True)
            final_archive.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    main()
