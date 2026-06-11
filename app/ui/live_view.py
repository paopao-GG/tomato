"""Live camera view with detection overlay and (fruit mode) pick controls.

The Tk update loop runs at ~30 FPS and draws the worker's most-recent
detections onto fresh camera frames, so video stays smooth even though
detections refresh at the Pi's ~2 FPS inference rate.
"""
from __future__ import annotations

import tkinter as tk
from collections import Counter

import cv2
import numpy as np
from PIL import Image, ImageTk

from .. import config
from ..detector import draw_detections

BG = "#0a0d10"
BAR = "#161b20"
DISP_W, DISP_H = 480, 360  # video display area (fits 800x480 with both bars)


class LiveViewScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.mode = config.MODE_FRUIT
        self._updating = False
        self._imgtk = None

        # --- top bar: back, title, fps ---
        top = tk.Frame(self, bg=BAR)
        top.pack(side="top", fill="x")
        tk.Button(top, text="< Back", font=("DejaVu Sans", 12, "bold"),
                  fg="#e8eef2", bg=BAR, activebackground="#262d34",
                  activeforeground="#e8eef2", relief="flat", bd=0,
                  command=self.app.show_mode_select).pack(side="left", padx=8, pady=6)
        self.title_lbl = tk.Label(top, text="", font=("DejaVu Sans", 14, "bold"),
                                  fg="#e8eef2", bg=BAR)
        self.title_lbl.pack(side="left", padx=6)
        self.fps_lbl = tk.Label(top, text="", font=("DejaVu Sans", 11),
                                fg="#8fa0ad", bg=BAR)
        self.fps_lbl.pack(side="right", padx=10)

        # --- video ---
        self.video = tk.Label(self, bg=BG, fg="#e07a7a")
        self.video.pack(side="top", expand=True)

        # --- detection summary ---
        self.summary = tk.Label(self, text="", font=("DejaVu Sans", 11),
                                fg="#c7d2da", bg=BG)
        self.summary.pack(side="top", pady=(0, 2))

        # --- fruit pick controls (shown only in fruit mode) ---
        self.controls = tk.Frame(self, bg="#11161b")
        self.pick_mode_var = tk.StringVar(value="manual")
        tk.Label(self.controls, text="Pick:", font=("DejaVu Sans", 11),
                 fg="#8fa0ad", bg="#11161b").pack(side="left", padx=(10, 4))
        for val, txt in (("manual", "Manual"), ("auto", "Auto")):
            tk.Radiobutton(self.controls, text=txt, value=val,
                           variable=self.pick_mode_var, font=("DejaVu Sans", 11),
                           fg="#e8eef2", bg="#11161b", selectcolor="#2a323a",
                           activebackground="#11161b", activeforeground="#e8eef2",
                           command=self._on_pick_mode).pack(side="left", padx=2)
        self.pick_btn = tk.Button(self.controls, text="PICK",
                                  font=("DejaVu Sans", 12, "bold"), fg="white",
                                  bg="#7a1f1f", activebackground="#a12a2a",
                                  activeforeground="white", relief="flat", bd=0,
                                  width=10, command=self._on_pick)
        self.pick_btn.pack(side="left", padx=12)
        self.pick_status = tk.Label(self.controls, text="", font=("DejaVu Sans", 10),
                                    fg="#8fa0ad", bg="#11161b")
        self.pick_status.pack(side="left", padx=8)

    # --- mode setup ------------------------------------------------------
    def configure_for_mode(self, mode: str):
        self.mode = mode
        spec = config.SPECS[mode]
        self.title_lbl.config(text=spec.label)
        if mode == config.MODE_FRUIT:
            self.controls.pack(side="bottom", fill="x", pady=4)
        else:
            self.controls.pack_forget()

    def _on_pick_mode(self):
        self.app.worker.set_pick_mode(self.pick_mode_var.get())

    def _on_pick(self):
        self.app.worker.manual_pick()

    # --- update loop -----------------------------------------------------
    def start_updates(self):
        if not self._updating:
            self._updating = True
            self._tick()

    def stop_updates(self):
        self._updating = False

    def _tick(self):
        if not self._updating:
            return
        self._render()
        self.after(33, self._tick)

    def _render(self):
        if not self.app.camera_ok:
            self.video.config(image="", text=f"Camera error:\n{self.app.camera_error}",
                              font=("DejaVu Sans", 14))
            return
        frame = self.app.camera.read()
        if frame is None:
            self.video.config(image="", text="Starting camera...",
                              fg="#8fa0ad", font=("DejaVu Sans", 14))
            return

        _, dets, fps = self.app.worker.snapshot()
        spec = config.SPECS[self.mode]
        draw_detections(frame, dets, spec)
        disp = self._fit(frame, DISP_W, DISP_H)
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self._imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.video.config(image=self._imgtk, text="")
        self.fps_lbl.config(text=f"{fps:4.1f} FPS")
        self.summary.config(text=self._summary_text(dets, spec))
        if self.mode == config.MODE_FRUIT:
            self.pick_status.config(text=self.app.pick_status)

    @staticmethod
    def _summary_text(dets, spec) -> str:
        if not dets:
            return "no detections"
        counts = Counter(d.name for d in dets)
        return "    ".join(f"{n}: {counts[n]}" for n in spec.names if counts[n])

    @staticmethod
    def _fit(frame, w, h):
        """Resize frame to fit (w, h) preserving aspect, centered on black."""
        fh, fw = frame.shape[:2]
        s = min(w / fw, h / fh)
        nw, nh = max(1, int(fw * s)), max(1, int(fh * s))
        resized = cv2.resize(frame, (nw, nh))
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        dx, dy = (w - nw) // 2, (h - nh) // 2
        canvas[dy:dy + nh, dx:dx + nw] = resized
        return canvas
