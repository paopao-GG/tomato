# Tomato Detector — UI + Camera + Live Detection

On-device app for the handheld tomato device (see [prd.md](prd.md)): a tkinter
touchscreen UI showing the live webcam feed with real-time YOLOv8 detection for
**leaf health** (healthy / unhealthy) and **fruit ripeness** (unripe / ripe /
overripe), plus a stubbed servo-scissor picker trigger.

## Run

```bash
./run.sh
# or
./.venv/bin/python -m app.main
```

- `F11` toggles fullscreen (use it on the 7" 800×480 screen); `Esc` exits.
- Pick a mode on the start screen. In **Fruit Picker** mode, choose **Manual**
  (tap **PICK**) or **Auto** (fires on ripe/overripe, debounced).

## How it works

- `app/camera.py` — threaded webcam capture (always exposes the latest frame).
- `app/detector.py` — shared YOLOv8 decoder + two backends.
- `app/pipeline.py` — background inference worker (~2 FPS) + auto-pick.
- `app/picker.py` — picker trigger; **stub** now, real `pyserial` path included
  but gated behind `config.SERIAL_ENABLED` (sends `b"PICK\n"` to the Arduino).
- `app/ui/` — `mode_select` and `live_view` screens; the UI draws the latest
  detections onto fresh frames at ~30 FPS so video stays smooth.

### Model backends (important)

Each model uses its one working export format (verified on this Pi):

| Model | Format used | Why |
|-------|-------------|-----|
| Fruit (`unripe/ripe/overripe`) | **ONNX** via onnxruntime | the NCNN export returns NaN |
| Leaf (`healthy/unhealthy`)     | **NCNN**                | the ONNX export is corrupt/truncated |

If you re-export the models, prefer fixing `ai-model/leaf/best.onnx` (currently
1.5 MB and unparseable) and the fruit NCNN; then both could share one backend.

## Dependencies

System Python is externally-managed (PEP 668) and `sudo` isn't available here,
so deps live in a venv created with `--system-site-packages` (to reuse the
system `tkinter` and `pyserial`):

```bash
python3 -m venv --system-site-packages .venv
./.venv/bin/python -m pip install opencv-python onnxruntime ncnn pillow
```

(`pillow` is installed into the venv to provide `PIL.ImageTk`, which the system
Pillow lacks.)

## Not yet wired (next steps)

- Real serial to the Arduino Mega: set `config.SERIAL_ENABLED = True` and the
  correct `SERIAL_PORT` once the servo-scissor hardware exists.
- Power source is still undecided (see the PRD).
