"""View: the CustomTkinter window. It only talks to the view model."""
from __future__ import annotations

import customtkinter as ctk

from model import Task
from viewmodel import PlannerViewModel

PRIORITY_VALUES = {"High": 1, "Medium": 2, "Low": 3}
PRIORITY_NAMES = {v: k for k, v in PRIORITY_VALUES.items()}


class PlannerView(ctk.CTk):
    def __init__(self, vm: PlannerViewModel):
        super().__init__()
        self.vm = vm
        self.title("Planner")
        self.geometry("580x660")
        self.minsize(480, 400)

        self._done_font = ctk.CTkFont(overstrike=True)
        self._build_ui()

        self.vm.subscribe(self._on_event)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll)
        self.vm.load()  # read the JSON file on boot (on the worker thread)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(self)
        form.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        self.title_entry = ctk.CTkEntry(form, placeholder_text="New task...")
        self.title_entry.grid(row=0, column=0, columnspan=3, padx=8, pady=(8, 4), sticky="ew")
        self.title_entry.bind("<Return>", lambda _e: self._add())

        self.due_entry = ctk.CTkEntry(form, placeholder_text="Due (YYYY-MM-DD)", width=150)
        self.due_entry.grid(row=1, column=0, padx=(8, 4), pady=(0, 8), sticky="w")

        self.priority_menu = ctk.CTkOptionMenu(form, values=list(PRIORITY_VALUES), width=100)
        self.priority_menu.set("Medium")
        self.priority_menu.grid(row=1, column=1, padx=4, pady=(0, 8))

        ctk.CTkButton(form, text="Add", width=80, command=self._add).grid(
            row=1, column=2, padx=(4, 8), pady=(0, 8)
        )

        self.task_list = ctk.CTkScrollableFrame(self)
        self.task_list.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")
        self.task_list.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(self, text="Loading...", anchor="w")
        self.status.grid(row=2, column=0, padx=14, pady=(0, 10), sticky="ew")

    # ------------------------------------------------------------------
    # User actions -> view model
    # ------------------------------------------------------------------
    def _add(self) -> None:
        self.vm.add_task(
            self.title_entry.get(),
            self.due_entry.get(),
            PRIORITY_VALUES[self.priority_menu.get()],
        )
        self.title_entry.delete(0, "end")
        self.due_entry.delete(0, "end")
        self.title_entry.focus()

    # ------------------------------------------------------------------
    # View model -> UI (always runs on the Tk thread via _poll)
    # ------------------------------------------------------------------
    def _poll(self) -> None:
        self.vm.pump()
        self.after(50, self._poll)

    def _on_event(self, kind: str, payload: object) -> None:
        if kind == "tasks":
            self._render(payload)  # type: ignore[arg-type]
        elif kind == "status":
            self.status.configure(text=str(payload), text_color=("gray20", "gray80"))
        elif kind == "error":
            self.status.configure(text=str(payload), text_color="#e5534b")

    def _render(self, tasks: list[Task]) -> None:
        for child in self.task_list.winfo_children():
            child.destroy()

        if not tasks:
            ctk.CTkLabel(self.task_list, text="Nothing planned yet.").grid(pady=20)
            return

        for row, t in enumerate(tasks):
            label = f"{t.title}   [{PRIORITY_NAMES.get(t.priority, 'Medium')}]"
            if t.due:
                label += f"   due {t.due}"

            box = ctk.CTkCheckBox(
                self.task_list,
                text=label,
                font=self._done_font if t.done else None,
                text_color="#e5534b" if t.is_overdue() else None,
                command=lambda tid=t.id: self.vm.toggle_done(tid),
            )
            if t.done:
                box.select()
            box.grid(row=row, column=0, padx=6, pady=4, sticky="w")

            ctk.CTkButton(
                self.task_list,
                text="✕",
                width=30,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                text_color=("gray20", "gray80"),
                command=lambda tid=t.id: self.vm.remove_task(tid),
            ).grid(row=row, column=1, padx=6, pady=4)

    def _on_close(self) -> None:
        self.vm.shutdown()  # flush any queued saves before exiting
        self.destroy()
