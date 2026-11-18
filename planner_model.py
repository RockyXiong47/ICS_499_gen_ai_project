"""Simple data structure for a planner app (UI-independent).

Your CustomTkinter code only talks to the Planner class, so the
data layer stays separate from the GUI.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class Task:
    title: str
    due: Optional[str] = None          # ISO date string, e.g. "2026-11-25"
    notes: str = ""
    priority: int = 2                  # 1 = high, 2 = medium, 3 = low
    done: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def is_overdue(self) -> bool:
        return bool(self.due) and not self.done and date.fromisoformat(self.due) < date.today()


class Planner:
    def __init__(self, filepath: str = "planner.json"):
        self.filepath = Path(filepath)
        self.tasks: list[Task] = []
        self.load()

    # ---- core operations ----
    def add(self, title: str, due: Optional[str] = None,
            notes: str = "", priority: int = 2) -> Task:
        task = Task(title=title, due=due, notes=notes, priority=priority)
        self.tasks.append(task)
        self.save()
        return task

    def remove(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.save()

    def toggle_done(self, task_id: str) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.done = not t.done
        self.save()

    def update(self, task_id: str, **changes) -> None:
        for t in self.tasks:
            if t.id == task_id:
                for key, value in changes.items():
                    setattr(t, key, value)
        self.save()

    # ---- views the UI can ask for ----
    def by_date(self, day: str) -> list[Task]:
        return [t for t in self.tasks if t.due == day]

    def pending(self) -> list[Task]:
        return sorted(
            (t for t in self.tasks if not t.done),
            key=lambda t: (t.due or "9999-12-31", t.priority),
        )

    # ---- persistence ----
    def save(self) -> None:
        self.filepath.write_text(json.dumps([asdict(t) for t in self.tasks], indent=2))

    def load(self) -> None:
        if self.filepath.exists():
            self.tasks = [Task(**d) for d in json.loads(self.filepath.read_text())]


if __name__ == "__main__":
    p = Planner("demo_planner.json")
    t = p.add("Finish Gen AI proposal", due="2026-11-25", priority=1)
    p.add("Buy groceries")
    p.toggle_done(t.id)
    for task in p.pending():
        print(task)
