"""Run with:  python main.py   (requires: pip install customtkinter)"""
from pathlib import Path

import customtkinter as ctk

from model import JsonStorage
from view import PlannerView
from viewmodel import PlannerViewModel

if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    # planner.json lives next to this script, so it loads the same way every boot.
    storage = JsonStorage(Path(__file__).with_name("planner.json"))
    app = PlannerView(PlannerViewModel(storage))
    app.mainloop()
