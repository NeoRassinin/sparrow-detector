import inspect

import cv2
import torch
from ultralytics import YOLO
from pathlib import Path
from ..config import (
    MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    IOU_THRESHOLD,
    PATCH_SHAPE_X,
    PATCH_SHAPE_Y,
    PATCH_OVERLAP_X,
    PATCH_OVERLAP_Y,
    PATCH_NMS_THRESHOLD,
    PATCH_MATCH_METRIC,
    PATCH_CONFIDENCE_THRESHOLD,
    PATCH_MERGE_IOU,
)

# PyTorch 2.6+ defaults torch.load(weights_only=True), which rejects the
# ultralytics checkpoint classes. The model is our own trained file (trusted
# source), so force weights_only=False on load.
_orig_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)


torch.load = _patched_torch_load

_model = None

# Forest green (BGR) — matches the frontend accent colour.
_BOX_COLOR = (91, 149, 52)


def get_model():
    global _model
    if _model is None:
        _model = YOLO(str(MODEL_PATH))
        _model.fuse()
    return _model


def _class_names() -> dict:
    return get_model().names or {}


def _count_sparrows(detections: list[dict]) -> int:
    """Count sparrows by class name; fall back to all boxes for single-class
    models whose only class isn't literally named "sparrow"."""
    names = [n.lower() for n in _class_names().values()]
    if "sparrow" in names:
        return sum(1 for d in detections if d["label"].lower() == "sparrow")
    return len(detections)


def _annotate(image_bgr, detections: list[dict]):
    """Draw boxes + confidence labels. Used for both inference modes so the
    saved annotated image looks the same regardless of how it was produced."""
    img = image_bgr.copy()
    h, w = img.shape[:2]
    thickness = max(2, round(w / 600))
    font_scale = max(0.4, w / 1800)
    for det in detections:
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        cv2.rectangle(img, (x1, y1), (x2, y2), _BOX_COLOR, thickness)
        text = f'{det["label"]} {det["confidence"] * 100:.0f}%'
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        ty = max(th + 6, y1)
        cv2.rectangle(img, (x1, ty - th - 6), (x1 + tw + 6, ty), _BOX_COLOR, -1)
        cv2.putText(
            img, text, (x1 + 3, ty - 4),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA,
        )
    return img


def _iou(a: dict, b: dict) -> float:
    ix1, iy1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
    ix2, iy2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
    area_b = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _merge_nms(detections: list[dict], iou_thr: float) -> list[dict]:
    """Class-agnostic greedy NMS over already-merged detection lists. Keeps the
    highest-confidence box and drops anything overlapping it above iou_thr."""
    kept: list[dict] = []
    for det in sorted(detections, key=lambda d: d["confidence"], reverse=True):
        if all(_iou(det, k) < iou_thr for k in kept):
            kept.append(det)
    return kept


def _detections_from_ultralytics(result) -> list[dict]:
    detections = []
    names = result.names or {}
    if result.boxes is not None:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                {
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                    "confidence": round(float(box.conf[0]), 3),
                    "label": names.get(int(box.cls[0]), "sparrow"),
                }
            )
    return detections


def run_inference_standard(image_bgr) -> list[dict]:
    model = get_model()
    results = model.predict(
        source=image_bgr,
        conf=CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
        device="cpu",
        verbose=False,
    )
    result = results[0] if results else None
    return _detections_from_ultralytics(result) if result else []


def run_inference_patched(image_bgr) -> list[dict]:
    """Tiled inference via patched_yolo_infer: slice into overlapping patches,
    detect per-patch at native resolution, then merge boxes back together."""
    from patched_yolo_infer import MakeCropsDetectThem, CombineDetections

    candidate = dict(
        image=image_bgr,
        segment=False,
        shape_x=PATCH_SHAPE_X,
        shape_y=PATCH_SHAPE_Y,
        overlap_x=PATCH_OVERLAP_X,
        overlap_y=PATCH_OVERLAP_Y,
        conf=PATCH_CONFIDENCE_THRESHOLD,
        iou=IOU_THRESHOLD,
        resize_initial_size=True,
        show_crops=False,
    )
    # Keep only kwargs this installed version accepts, and reuse the already
    # loaded model when supported (otherwise the lib reloads weights by path).
    params = inspect.signature(MakeCropsDetectThem.__init__).parameters
    crop_kwargs = {k: v for k, v in candidate.items() if k in params}
    if "model" in params:
        crop_kwargs["model"] = get_model()
    else:
        crop_kwargs["model_path"] = str(MODEL_PATH)

    element_crops = MakeCropsDetectThem(**crop_kwargs)
    combined = CombineDetections(
        element_crops,
        nms_threshold=PATCH_NMS_THRESHOLD,
        match_metric=PATCH_MATCH_METRIC,
    )

    detections = []
    for box, conf, name in zip(
        combined.filtered_boxes,
        combined.filtered_confidences,
        combined.filtered_classes_names,
    ):
        x1, y1, x2, y2 = box
        detections.append(
            {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
                "confidence": round(float(conf), 3),
                "label": str(name),
            }
        )
    return detections


def run_inference(image_path: str | Path, use_patches: bool = False):
    """Run detection and return (detections, annotated_bgr_image, sparrow_count).

    use_patches=True enables tiled inference for far-plane / dense scenes; it is
    slower (N patches = N forward passes) but recalls many more small birds.
    """
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise ValueError("Could not read image")

    h, w = image_bgr.shape[:2]
    # Tiling only makes sense when the image is larger than a single patch.
    # For smaller images the library would produce zero tiles (IndexError) or a
    # single upscaled tile, so fall back to plain full-image inference.
    can_tile = w >= PATCH_SHAPE_X and h >= PATCH_SHAPE_Y

    if use_patches and can_tile:
        # Hybrid (SAHI-style): always keep the full-image pass so large birds
        # split across tile borders aren't lost, then add small birds the tiles
        # recovered, deduping overlaps via NMS.
        detections = _merge_nms(
            run_inference_standard(image_bgr) + run_inference_patched(image_bgr),
            PATCH_MERGE_IOU,
        )
    else:
        detections = run_inference_standard(image_bgr)

    annotated = _annotate(image_bgr, detections)
    return detections, annotated, _count_sparrows(detections)


def save_annotated(image_bgr, path: str | Path):
    cv2.imwrite(str(path), image_bgr)
