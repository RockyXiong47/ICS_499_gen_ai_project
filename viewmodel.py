"""View model: owns the task list and does all work on a background thread.

Threading design
----------------
* The UI thread calls commands (add_task, toggle_done, ...). They return
  immediately after putting a job on a queue.
* One worker thread runs the jobs in order (so file saves never race each
  other), mutates the task list under a lock, and saves to disk.
* The worker never touches Tk. It posts events to a second queue, and the
  view calls pump() on the UI thread to receive them. Tk is not thread-safe,
  so this hand-off is what keeps the app stable.
"""
from __future__ import annotations

import dataclasses
import queue
import threading
from datetime import date
from typing import Callable, Optional

from model import JsonStorage, Task


class PlannerViewModel:
    def __init__(self, storage: Optional[JsonStorage] = None):
        self._storage = storage or JsonStorage()
        self._tasks: list[Task] = []
        self._lock = threading.Lock()
        self._jobs: queue.Queue = queue.Queue()
        self._events: queue.Queue = queue.Queue()
        self._subscribers: list[Callable[[str, object], None]] = []
        self._worker = threading.Thread(target=self._run, name="planner-worker", daemon=True)
        self._worker.start()

    # ------------------------------------------------------------------
    # Observer plumbing (UI thread)
    # ------------------------------------------------------------------
    def subscribe(self, callback: Callable[[str, object], None]) -> None:
        self._subscribers.append(callback)

    def pump(self) -> None:
        """Deliver pending events to subscribers. Call from the UI thread."""
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                return
            for cb in self._subscribers:
                cb(kind, payload)

    # ------------------------------------------------------------------
    # Commands (UI thread -> returns immediately)
    # ------------------------------------------------------------------
    def load(self) -> None:
        self._jobs.put(self._do_load)

    def add_task(self, title: str, due: str = "", priority: int = 2) -> None:
        title, due = title.strip(), due.strip()
        if not title:
            self._emit("error", "Please enter a task title.")
            return
        if due:
            try:
                date.fromisoformat(due)
            except ValueError:
                self._emit("error", "Due date must look like YYYY-MM-DD.")
                return
        self._jobs.put(lambda: self._do_add(title, due or None, priority))

    def toggle_done(self, task_id: str) -> None:
        self._jobs.put(lambda: self._do_toggle(task_id))

    def remove_task(self, task_id: str) -> None:
        self._jobs.put(lambda: self._do_remove(task_id))

    def shutdown(self) -> None:
        """Finish queued jobs (including saves), then stop the worker."""
        self._jobs.put(None)
        self._worker.join(timeout=5)

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------
    def _run(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
            try:
                job()
            except Exception as exc:  # keep the worker alive no matter what
                self._emit("error", f"Something went wrong: {exc}")

    def _do_load(self) -> None:
        loaded = self._storage.load()
        with self._lock:
            self._tasks = loaded
        self._publish(f"Loaded {len(loaded)} task(s).")

    def _do_add(self, title: str, due: Optional[str], priority: int) -> None:
        with self._lock:
            self._tasks.append(Task(title=title, due=due, priority=priority))
        self._save_and_publish()

    def _do_toggle(self, task_id: str) -> None:
        with self._lock:
            for t in self._tasks:
                if t.id == task_id:
                    t.done = not t.done
        self._save_and_publish()

    def _do_remove(self, task_id: str) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.id != task_id]
        self._save_and_publish()

    def _save_and_publish(self) -> None:
        with self._lock:
            snapshot = list(self._tasks)
        self._storage.save(snapshot)
        self._publish("Saved.")

    def _publish(self, status: str) -> None:
        """Send the view a sorted copy of the tasks so it never touches shared state."""
        with self._lock:
            copies = [dataclasses.replace(t) for t in self._tasks]
        copies.sort(key=lambda t: (t.done, t.due or "9999-12-31", t.priority))
        self._emit("tasks", copies)
        self._emit("status", status)

    def _emit(self, kind: str, payload: object) -> None:
        self._events.put((kind, payload))
