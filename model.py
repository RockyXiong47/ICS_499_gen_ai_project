"""Model layer: the Task data structure and JSON persistence."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class Task:
    title: str
    due: Optional[str] = None      # ISO date string, e.g. "2026-11-25"
    notes: str = ""
    priority: int = 2              # 1 = high, 2 = medium, 3 = low
    done: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def is_overdue(self) -> bool:
        if not self.due or self.done:
            return False
        try:
            return date.fromisoformat(self.due) < date.today()
        except ValueError:
            return False


class JsonStorage:
    """Reads and writes the task list as a JSON file."""

    def __init__(self, path: str | Path = "planner.json"):
        self.path = Path(path)

    def load(self) -> list[Task]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Task(**d) for d in data]
        except (json.JSONDecodeError, TypeError, OSError):
            # Unreadable file: set it aside so it isn't overwritten, start fresh.
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            return []

    def save(self, tasks: list[Task]) -> None:
        payload = json.dumps([asdict(t) for t in tasks], indent=2)
        # Write to a temp file, then swap it in, so a crash can't leave a half-written file.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, self.path)
