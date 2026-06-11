"""Entry point: run with `python -m app.main` (or ./run.sh)."""
from __future__ import annotations

import tkinter as tk

from .ui.app import App


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
