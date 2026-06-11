# Tomato Fruit Picker & Leaf Health Detector
> A handheld Raspberry Pi device that uses on-device computer vision to (1) grade
> tomato ripeness and snip ripe fruit, and (2) flag unhealthy tomato leaves.
> Built as a demo/teaching tool for agriculture students and researchers.

## 1. Problem & Goal
**Problem:** Judging tomato ripeness and spotting early leaf disease by eye is
subjective and inconsistent — a real friction point for students and researchers
learning crop assessment. There's no simple, portable tool that demonstrates
automated maturity grading and leaf-health screening in one handheld unit.

**Goals:**
1. Detect whether a tomato leaf is healthy or unhealthy from a live camera feed.
2. Classify tomato fruit ripeness as unripe / ripe / overripe.
3. Snip ripe/overripe fruit with a servo-driven scissor (automatic or manual).
4. Run fully on-device (no internet) on a Raspberry Pi with a touchscreen UI.

## 2. Target Users & Use Cases
Primary users: **agriculture students and researchers** using the device as a
hands-on demo/teaching tool.

| User | Scenario | Outcome |
|------|----------|---------|
| May (fruit) | Unsure if a tomato is ready. Points the camera at the fruit and reads the LCD. | Model labels the fruit unripe/ripe/overripe and boxes it. If ripe/overripe, the scissor can snip it (auto or manual). If unripe, the screen boxes it and shows "not ripe." |
| Yumi (leaf) | Wants to check plant health. Points the camera at a leaf. | Screen boxes the leaf and shows "healthy" or "unhealthy." |

## 3. System Overview
Two selectable modes share one camera + screen; only Fruit mode drives the picker.

```
            +---------------------- Raspberry Pi 4B ----------------------+
 USB Webcam |  OpenCV capture -> YOLOv8 (NCNN) inference -> tkinter UI    |
 ---------> |  Mode select: [Leaf health] / [Fruit picker]               |
            |  Pick trigger: auto on ripe/overripe, or manual button      |
            +---------------------------+---------------------------------+
                                        | USB serial (command)
                                        v
                              +------------------+     +---------------------+
                              |   Arduino Mega   |---> | Servo scissor/snips |
                              | (servo driver)   |     | (cuts fruit stem)   |
                              +------------------+     +---------------------+
            Display: 7" HDMI touchscreen (800x480)
```

## 4. Hardware Requirements
**Main unit**
- Raspberry Pi 4B — inference + UI
- USB webcam — live feed
- 7" HDMI touchscreen, 800x480 — UI + touch input

**Picker mechanism**
- Arduino Mega — receives serial command, drives the servo
- Servo motor driving a **scissor/snips** that closes on the fruit stem to cut it

**Open item — power source (undecided):** must support Pi + screen + servo.
Note the Pi 4B (~5V/3A), the 7" screen, and servo current spikes; a separate or
well-regulated supply for the servo is recommended to avoid Pi brownouts.

## 5. Software Requirements
**Raspberry Pi (Python)**
- UI: tkinter — startup mode-select; live feed with detection overlay (boxes + labels).
- Vision: Ultralytics YOLOv8 via the **NCNN** export (ARM-optimized); OpenCV for capture/draw.
- Loads the leaf model or the fruit model depending on the selected mode.
- Fruit mode pick-toggle: **Automatic** (snip on ripe/overripe) or **Manual** (tap to snip).
- Sends the pick command to the Arduino over USB serial.

**Arduino Mega (C/C++)**
- Listens on serial; on the pick command, runs the servo cut cycle
  (close -> cut -> open), then optionally acks.

**Proposed serial protocol (example):** Pi sends `PICK\n`; Arduino runs the cut
cycle and replies `DONE\n`. Simple ASCII, easy to debug.

## 6. AI / ML Models
Both are **Ultralytics YOLOv8 detection** models (v8.3.40), trained at **640x640**,
exported to PyTorch / ONNX / TorchScript / **NCNN** (NCNN used on the Pi for speed).

| Model | Location | Classes |
|-------|----------|---------|
| Leaf health | `ai-model/leaf/` | `leaf_healthy`, `leaf_unhealthy` |
| Fruit maturity | `ai-model/leaf/tomato/` | `fruit_unripe`, `fruit_ripe`, `fruit_overripe` |

Note: the leaf model is **binary** (healthy vs unhealthy) — it does not identify a
specific disease.

## 7. Functional Requirements
**Must**
- F1: On startup, user selects Leaf or Fruit mode via touchscreen.
- F2: Show live camera feed with bounding boxes + class labels on the LCD.
- F3: Leaf mode shows healthy/unhealthy per detected leaf.
- F4: Fruit mode shows unripe/ripe/overripe per detected fruit.
- F5: In Fruit mode, ripe/overripe detections can trigger the servo scissor.
- F6: User can switch between Automatic and Manual pick modes.
- F7: Pi triggers the Arduino servo over serial.

**Should**
- F8: On-screen feedback when a pick command is sent / completed.
- F9: Return to mode-select / switch modes without restarting.

## 8. Data Flow
1. UI starts -> user picks **Fruit** or **Leaf** mode (touch).
2. Webcam streams to the Pi; each frame runs the mode's YOLOv8 (NCNN) model.
3. Detections (boxes + labels) are drawn on the 7" LCD in real time.
4. **Leaf mode:** display healthy/unhealthy only.
5. **Fruit mode:** display unripe/ripe/overripe.
   - ripe/overripe AND pick mode = Automatic -> Pi sends `PICK` over serial.
   - pick mode = Manual -> Pi sends `PICK` only when the user taps the button.
6. Arduino receives the command -> servo scissor snips the stem -> optional `DONE` ack.

## 9. Non-Functional Requirements
- **Performance:** usable real-time feedback on the Pi 4B (NCNN chosen for this;
  expect a few FPS at 640x640 — acceptable for a handheld demo).
- **Offline:** fully on-device, no internet required.
- **Usability:** readable labels/boxes on the 800x480 screen; single-tap controls.
- **Accuracy:** bounded by the trained models and lighting; best in good, even light.

## 10. Constraints & Assumptions
- **Power source undecided** — must run Pi + screen + servo; servo spikes argue for
  a separate supply. (Open decision.)
- Raspberry Pi 4B compute limits real-time FPS; NCNN export chosen to mitigate.
- Leaf model is binary (no disease type); fruit model is 3-class.
- Detection quality depends on lighting, focus, and distance.
- Assumes USB webcam + USB serial link to the Arduino Mega.

## 11. Out of Scope (this version)
- Identifying *specific* leaf diseases or pests.
- Yield counting, logging, or cloud/dashboard sync.
- Detecting fruits/leaves other than tomato.
- Autonomous navigation / robotic arm (device is handheld, human-aimed).
- Battery-life optimization (pending the power decision).
