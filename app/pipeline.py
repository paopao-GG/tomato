"""Background inference worker.

Runs detection on the latest camera frame in its own thread at whatever rate
the Pi can manage (~1.5-2 FPS). It publishes only the detection results + FPS;
the UI draws those boxes onto fresh, high-rate camera frames, so the video
stays smooth even though detections update slowly. Also handles the fruit-mode
auto-pick trigger (debounced).
"""
from __future__ import annotations

import threading
import time

from . import config
from .detector import Detection, build_detector


class InferenceWorker:
    def __init__(self, camera, picker):
        self.camera = camera
        self.picker = picker

        # Preload both detectors once so mode switches are instant.
        self.detectors = {mode: build_detector(spec)
                          for mode, spec in config.SPECS.items()}

        self._lock = threading.Lock()
        self._mode = config.MODE_FRUIT
        self._pick_mode = "manual"          # "manual" | "auto"
        self._dets: list[Detection] = []
        self._fps = 0.0
        self._last_autopick = 0.0

        self._running = False
        self._thread: threading.Thread | None = None

    # --- control (called from UI thread) ---------------------------------
    def set_mode(self, mode: str):
        with self._lock:
            self._mode = mode
            self._dets = []                 # drop stale boxes from old mode

    def set_pick_mode(self, pick_mode: str):
        with self._lock:
            self._pick_mode = pick_mode

    def manual_pick(self):
        self.picker.trigger("manual")

    # --- snapshot for the UI ---------------------------------------------
    def snapshot(self):
        with self._lock:
            return self._mode, list(self._dets), self._fps

    # --- lifecycle -------------------------------------------------------
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for det in self.detectors.values():
            det.close()

    def _loop(self):
        while self._running:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.02)
                continue

            with self._lock:
                mode = self._mode
                pick_mode = self._pick_mode

            t0 = time.time()
            dets = self.detectors[mode].detect(frame)
            dt = time.time() - t0

            if mode == config.MODE_FRUIT and pick_mode == "auto":
                self._maybe_autopick(dets)

            with self._lock:
                # Only publish if mode hasn't changed mid-inference.
                if mode == self._mode:
                    self._dets = dets
                    inst = 1.0 / dt if dt > 0 else 0.0
                    self._fps = inst if self._fps == 0 else 0.8 * self._fps + 0.2 * inst

    def _maybe_autopick(self, dets: list[Detection]):
        if not any(d.name in config.FRUIT_PICK_CLASSES for d in dets):
            return
        now = time.time()
        if now - self._last_autopick >= config.AUTOPICK_DEBOUNCE_S:
            self._last_autopick = now
            self.picker.trigger("auto")
