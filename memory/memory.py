"""Small, local, bounded SQLite memory and personal task list."""
import sqlite3
import threading
from pathlib import Path
from datetime import date


class MemoryStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, user_text TEXT NOT NULL, assistant_text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, due_date TEXT, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, fact TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute("PRAGMA busy_timeout=15000")
        return db

    def save_turn(self, user_text: str, assistant_text: str) -> None:
        with self._write_lock:
            with self._connect() as db:
                db.execute("INSERT INTO turns(user_text, assistant_text) VALUES (?, ?)", (user_text, assistant_text))
                db.execute("DELETE FROM turns WHERE id NOT IN (SELECT id FROM turns ORDER BY id DESC LIMIT 500)")


    def recent_messages(self, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute("SELECT user_text, assistant_text FROM turns ORDER BY id DESC LIMIT ?", (max(0, limit),)).fetchall()
        result = []
        for user_text, assistant_text in reversed(rows):
            result.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": assistant_text}])
        return result

    def remember_fact(self, fact: str) -> dict:
        fact = " ".join(fact.split())
        if not fact or len(fact) > 1000:
            return {"success": False, "error": "Memory must contain 1–1000 characters"}
        with self._write_lock:
            with self._connect() as db:
                db.execute("INSERT OR IGNORE INTO memories(fact) VALUES (?)", (fact,))
                row = db.execute("SELECT id FROM memories WHERE fact=?", (fact,)).fetchone()
        return {"success": True, "memory_id": row[0], "fact": fact}

    def list_memories(self, limit: int = 30) -> dict:
        limit = max(1, min(int(limit), 100))
        with self._connect() as db:
            rows = db.execute("SELECT id, fact, created_at FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"success": True, "memories": [dict(zip(("id", "fact", "created_at"), row)) for row in rows]}

    def recent_memories(self, limit: int = 20) -> list[str]:
        with self._connect() as db:
            rows = db.execute("SELECT fact FROM memories ORDER BY id DESC LIMIT ?", (max(0, min(int(limit), 100)),)).fetchall()
        return [row[0] for row in reversed(rows)]

    def forget_memory(self, memory_id: int) -> dict:
        with self._write_lock:
            with self._connect() as db:
                cur = db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        if not cur.rowcount:
            return {"success": False, "error": "No saved memory with that id"}
        return {"success": True, "forgotten_memory_id": memory_id}

    def create_task(self, title: str, due_date: str | None = None) -> dict:
        title = title.strip()
        if not title or len(title) > 500:
            return {"success": False, "error": "Task title must contain 1–500 characters"}
        if due_date:
            try:
                due_date = date.fromisoformat(due_date).isoformat()
            except ValueError:
                return {"success": False, "error": "due_date must use YYYY-MM-DD"}
        with self._write_lock:
            with self._connect() as db:
                cur = db.execute("INSERT INTO tasks(title, due_date) VALUES (?, ?)", (title, due_date))
                task_id = cur.lastrowid
        return {"success": True, "task": {"id": task_id, "title": title, "due_date": due_date, "status": "open"}}

    def list_tasks(self, status: str = "open") -> dict:
        if status not in {"open", "done", "all"}:
            return {"success": False, "error": "status must be open, done, or all"}
        with self._connect() as db:
            if status == "all":
                rows = db.execute("SELECT id, title, due_date, status, created_at FROM tasks ORDER BY COALESCE(due_date, '9999-12-31'), id").fetchall()
            else:
                rows = db.execute("SELECT id, title, due_date, status, created_at FROM tasks WHERE status=? ORDER BY COALESCE(due_date, '9999-12-31'), id", (status,)).fetchall()
        return {"success": True, "tasks": [dict(zip(("id", "title", "due_date", "status", "created_at"), r)) for r in rows]}

    def complete_task(self, task_id: int) -> dict:
        with self._write_lock:
            with self._connect() as db:
                cur = db.execute("UPDATE tasks SET status='done' WHERE id=? AND status='open'", (task_id,))
        if not cur.rowcount:
            return {"success": False, "error": "No open task with that id"}
        return {"success": True, "task_id": task_id, "status": "done"}


