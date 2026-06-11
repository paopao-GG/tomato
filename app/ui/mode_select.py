"""Startup screen: pick Fruit Picker or Leaf Health mode."""
from __future__ import annotations

import tkinter as tk

from .. import config

BG = "#101418"


class ModeSelectScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app

        tk.Label(self, text="Tomato Detector", font=("DejaVu Sans", 28, "bold"),
                 fg="#e8eef2", bg=BG).pack(pady=(46, 4))
        tk.Label(self, text="Choose a mode", font=("DejaVu Sans", 14),
                 fg="#8fa0ad", bg=BG).pack(pady=(0, 26))

        btns = tk.Frame(self, bg=BG)
        btns.pack()
        self._button(btns, "Fruit Picker", "ripeness + auto/manual pick",
                     "#7a1f1f", config.MODE_FRUIT).grid(row=0, column=0, padx=14)
        self._button(btns, "Leaf Health", "healthy / unhealthy",
                     "#1f5f2a", config.MODE_LEAF).grid(row=0, column=1, padx=14)

        tk.Label(self, text="F11 fullscreen   |   Esc exit",
                 font=("DejaVu Sans", 10), fg="#5f6e79", bg=BG).pack(side="bottom", pady=10)

    def _button(self, parent, title, subtitle, color, mode):
        wrap = tk.Frame(parent, bg=color, width=240, height=170)
        wrap.pack_propagate(False)
        btn = tk.Button(wrap, text=f"{title}\n\n{subtitle}",
                        font=("DejaVu Sans", 16, "bold"), fg="white", bg=color,
                        activebackground=color, activeforeground="white",
                        relief="flat", bd=0, wraplength=210,
                        command=lambda: self.app.start_mode(mode))
        btn.pack(fill="both", expand=True)
        return wrap
