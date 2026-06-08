import torch
from ultralytics import YOLO
from pathlib import Path
from ..config import MODEL_PATH, CONFIDENCE_THRESHOLD, IOU_THRESHOLD

# PyTorch 2.6+ defaults torch.load(weights_only=True), which rejects the
# ultralytics checkpoint classes. The model is our own trained file (trusted
# source), so force weights_only=False on load.
_orig_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)


torch.load = _patched_torch_load

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(str(MODEL_PATH))
        _model.fuse()
    return _model


def run_inference(image_path: str | Path):
    model = get_model()
    results = model.predict(
        source=str(image_path),
        conf=CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
        device="cpu",
    )
    return results[0] if results else None
