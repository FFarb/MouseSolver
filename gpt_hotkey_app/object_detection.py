"""Object detection module using YOLOv8."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from ultralytics import YOLO

if TYPE_CHECKING:
    from PIL.Image import Image

_model = None


def _get_model() -> YOLO:
    """Lazy-load and return the YOLOv8n model."""
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")  # This will auto-download the model on first use
    return _model


def detect_objects_pil(
    img: Image, conf: float = 0.3, iou: float = 0.45
) -> List[Tuple[int, int, int, int, float, str]]:
    """Detect objects in a PIL Image using YOLOv8n.

    Args:
        img: The input PIL Image.
        conf: The confidence threshold for detection.
        iou: The IoU threshold for non-max suppression.

    Returns:
        A list of tuples, where each tuple contains (x1, y1, x2, y2, score, class_name).
    """
    model = _get_model()
    arr = np.array(img.convert("RGB"))
    res = model.predict(source=arr, conf=conf, iou=iou, verbose=False)
    out = []

    if not res:
        return out

    r = res[0]
    names = r.names
    boxes = getattr(r, "boxes", None)
    if boxes is None:
        return out

    for (x1, y1, x2, y2), sc, cls in zip(
        boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), boxes.cls.cpu().numpy()
    ):
        out.append(
            (int(x1), int(y1), int(x2), int(y2), float(sc), names.get(int(cls), str(int(cls))))
        )
    return out
