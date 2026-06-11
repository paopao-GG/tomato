"""YOLOv8 detection with a shared decoder and two interchangeable backends.

The fruit model runs through onnxruntime and the leaf model through ncnn, but
both emit the same raw YOLOv8 detect tensor of shape (4 + num_classes, 8400):
rows 0-3 are box center x, y, w, h in letterboxed-input pixels; the remaining
rows are per-class scores (already activated). The BaseDetector turns that into
boxes in original-frame coordinates and runs NMS, so the backends only have to
produce the raw tensor.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from . import config


@dataclass
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    cls: int
    name: str
    score: float


def letterbox(img: np.ndarray, size: int):
    """Resize keeping aspect ratio, pad to a square (size x size).

    Returns (canvas, ratio, dx, dy) so detections can be mapped back.
    """
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    dx, dy = (size - nw) // 2, (size - nh) // 2
    canvas[dy:dy + nh, dx:dx + nw] = resized
    return canvas, r, dx, dy


class BaseDetector:
    def __init__(self, spec: config.ModelSpec, conf: float, iou: float, size: int):
        self.spec = spec
        self.names = spec.names
        self.colors = spec.colors
        self.conf = conf
        self.iou = iou
        self.size = size

    # Backends implement this: letterboxed BGR image -> (4 + nc, 8400) array.
    def _infer(self, lb_bgr: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def close(self):
        """Release native resources. Override in backends as needed."""

    def detect(self, frame: np.ndarray) -> list[Detection]:
        lb, r, dx, dy = letterbox(frame, self.size)
        raw = self._infer(lb)
        return self._decode(raw, r, dx, dy)

    def _decode(self, raw: np.ndarray, r: float, dx: int, dy: int) -> list[Detection]:
        out = raw.T  # (8400, 4 + nc)
        boxes = out[:, :4]
        scores_all = out[:, 4:]
        cls = np.argmax(scores_all, axis=1)
        conf = scores_all[np.arange(scores_all.shape[0]), cls]

        keep = conf >= self.conf
        if not np.any(keep):
            return []
        boxes, cls, conf = boxes[keep], cls[keep], conf[keep]

        # center xywh (letterbox space) -> top-left xywh in original frame
        cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        x = (cx - w / 2 - dx) / r
        y = (cy - h / 2 - dy) / r
        w, h = w / r, h / r
        rects = np.stack([x, y, w, h], axis=1)

        idxs = cv2.dnn.NMSBoxes(rects.tolist(), conf.tolist(), self.conf, self.iou)
        if len(idxs) == 0:
            return []

        dets: list[Detection] = []
        for i in np.array(idxs).flatten():
            xi, yi, wi, hi = rects[i]
            c = int(cls[i])
            dets.append(Detection(
                x1=int(xi), y1=int(yi), x2=int(xi + wi), y2=int(yi + hi),
                cls=c, name=self.names[c], score=float(conf[i]),
            ))
        return dets


class OnnxDetector(BaseDetector):
    def __init__(self, spec, conf, iou, size, threads):
        super().__init__(spec, conf, iou, size)
        import onnxruntime as ort
        ort.set_default_logger_severity(3)  # silence GPU-probe warnings
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(
            str(spec.path), so, providers=["CPUExecutionProvider"])
        self.input_name = self.sess.get_inputs()[0].name

    def _infer(self, lb_bgr):
        rgb = cv2.cvtColor(lb_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        x = np.ascontiguousarray(rgb.transpose(2, 0, 1)[None])  # (1,3,H,W)
        out = self.sess.run(None, {self.input_name: x})[0]
        return out[0]  # (4 + nc, 8400)

    def close(self):
        self.sess = None


class NcnnDetector(BaseDetector):
    def __init__(self, spec, conf, iou, size, threads):
        super().__init__(spec, conf, iou, size)
        import ncnn
        self._ncnn = ncnn
        self.net = ncnn.Net()
        self.net.opt.use_vulkan_compute = False
        self.net.opt.num_threads = threads
        self.net.load_param(str(spec.path / "model.ncnn.param"))
        self.net.load_model(str(spec.path / "model.ncnn.bin"))

    def _infer(self, lb_bgr):
        rgb = cv2.cvtColor(lb_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        chw = np.ascontiguousarray(rgb.transpose(2, 0, 1))  # (3,H,W)
        ex = self.net.create_extractor()
        # .clone() keeps the Mat's buffer alive for the extractor's lifetime
        ex.input("in0", self._ncnn.Mat(chw).clone())
        _, out0 = ex.extract("out0")
        return np.array(out0)  # (4 + nc, 8400)

    def close(self):
        # Explicitly free the ncnn Net to avoid a crash during interpreter
        # teardown (otherwise GC order can destroy its allocator too early).
        if self.net is not None:
            self.net.clear()
            self.net = None


def build_detector(spec: config.ModelSpec) -> BaseDetector:
    kwargs = dict(conf=config.CONF_THRESHOLD, iou=config.IOU_THRESHOLD,
                  size=config.INPUT_SIZE, threads=config.NUM_THREADS)
    if spec.backend == "onnx":
        return OnnxDetector(spec, **kwargs)
    if spec.backend == "ncnn":
        return NcnnDetector(spec, **kwargs)
    raise ValueError(f"unknown backend: {spec.backend}")


def draw_detections(frame: np.ndarray, dets: list[Detection],
                    spec: config.ModelSpec) -> np.ndarray:
    """Draw boxes + labels onto a copy of frame (BGR)."""
    out = frame
    for d in dets:
        color = spec.colors[d.cls]
        cv2.rectangle(out, (d.x1, d.y1), (d.x2, d.y2), color, 2)
        label = f"{d.name} {d.score:.2f}"
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ytop = max(0, d.y1 - th - bl - 2)
        cv2.rectangle(out, (d.x1, ytop), (d.x1 + tw + 4, ytop + th + bl + 2), color, -1)
        cv2.putText(out, label, (d.x1 + 2, ytop + th),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return out
