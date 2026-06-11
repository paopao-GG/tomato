"""Central configuration: model specs, classes, thresholds, colors, serial.

Backend choice per model is deliberate and verified on this Pi:
  - Fruit model: ONNX via onnxruntime  (the NCNN export returns NaN)
  - Leaf  model: NCNN                  (the ONNX export is corrupt/truncated)
Both are YOLOv8 detection heads producing a (4 + num_classes, 8400) tensor.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --- Paths ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "ai-model"

# --- Camera --------------------------------------------------------------
CAM_INDEX = 0          # /dev/video0 (USB UVC webcam)
CAM_WIDTH = 640
CAM_HEIGHT = 480

# --- Inference -----------------------------------------------------------
INPUT_SIZE = 640       # YOLOv8 square input
CONF_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45
NUM_THREADS = 4        # Pi 4B has 4 cores

# --- Picker / auto-pick --------------------------------------------------
AUTOPICK_DEBOUNCE_S = 3.0   # min seconds between automatic pick triggers

# Real serial to the Arduino Mega is wired but disabled until hardware exists.
SERIAL_ENABLED = False
SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUD = 9600
SERIAL_PICK_CMD = b"PICK\n"

# --- Modes ---------------------------------------------------------------
MODE_LEAF = "leaf"
MODE_FRUIT = "fruit"

# --- Colors (BGR, for OpenCV drawing) ------------------------------------
GREEN = (0, 180, 0)
RED = (0, 0, 220)
ORANGE = (0, 140, 255)
DARKRED = (40, 20, 140)


@dataclass(frozen=True)
class ModelSpec:
    mode: str
    backend: str            # "onnx" | "ncnn"
    path: Path              # .onnx file (onnx) or model dir (ncnn)
    names: tuple[str, ...]  # class index -> name (order matters!)
    colors: tuple[tuple[int, int, int], ...]  # parallel to names, BGR
    label: str              # human label for the UI


# Class order taken directly from each model's metadata.yaml.
LEAF_SPEC = ModelSpec(
    mode=MODE_LEAF,
    backend="ncnn",
    path=MODELS_DIR / "leaf" / "best_ncnn_model",
    names=("leaf_healthy", "leaf_unhealthy"),
    colors=(GREEN, RED),
    label="Leaf Health",
)

FRUIT_SPEC = ModelSpec(
    mode=MODE_FRUIT,
    backend="onnx",
    path=MODELS_DIR / "leaf" / "tomato" / "best.onnx",
    names=("fruit_overripe", "fruit_ripe", "fruit_unripe"),
    colors=(DARKRED, RED, GREEN),
    label="Fruit Picker",
)

SPECS = {MODE_LEAF: LEAF_SPEC, MODE_FRUIT: FRUIT_SPEC}

# Detections of these fruit classes are "pickable" (trigger the scissor).
FRUIT_PICK_CLASSES = ("fruit_ripe", "fruit_overripe")
