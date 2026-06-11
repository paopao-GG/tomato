"""Top-level app controller: owns camera, picker, worker, and the two screens."""
from __future__ import annotations

import tkinter as tk

from .. import config
from ..camera import Camera
from ..picker import Picker
from ..pipeline import InferenceWorker
from .live_view import LiveViewScreen
from .mode_select import ModeSelectScreen


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tomato Detector")
        self.root.geometry("800x480")          # 7" touchscreen native size
        self.root.configure(bg="#101418")
        self.fullscreen = False
        self.pick_status = "idle"

        # --- hardware + pipeline ---
        self.camera = Camera(config.CAM_INDEX, config.CAM_WIDTH, config.CAM_HEIGHT)
        self.camera_ok = True
        self.camera_error = ""
        try:
            self.camera.start()
        except Exception as e:  # noqa: BLE001 - keep UI alive, show the error
            self.camera_ok = False
            self.camera_error = str(e)

        self.picker = Picker(status_cb=self._on_pick_status)
        self.worker = InferenceWorker(self.camera, self.picker)
        self.worker.start()

        # --- stacked screens ---
        self.container = tk.Frame(root, bg="#101418")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.mode_select = ModeSelectScreen(self.container, self)
        self.live_view = LiveViewScreen(self.container, self)
        for screen in (self.mode_select, self.live_view):
            screen.grid(row=0, column=0, sticky="nsew")

        self.show_mode_select()

        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._on_escape)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    # --- picker status (called from any thread; only stores a string) ----
    def _on_pick_status(self, msg: str):
        self.pick_status = msg

    # --- screen navigation ----------------------------------------------
    def show_mode_select(self):
        self.live_view.stop_updates()
        self.mode_select.tkraise()

    def start_mode(self, mode: str):
        self.worker.set_mode(mode)
        self.live_view.configure_for_mode(mode)
        self.live_view.tkraise()
        self.live_view.start_updates()

    # --- window controls -------------------------------------------------
    def _toggle_fullscreen(self, _event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def _on_escape(self, _event=None):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)
        else:
            self.shutdown()

    def shutdown(self):
        try:
            self.worker.stop()
            self.camera.stop()
            self.picker.close()
        finally:
            self.root.destroy()
