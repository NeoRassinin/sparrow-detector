import json
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from ..models.database import (
    get_detections,
    get_detection_by_id,
    delete_detection,
    get_total_count,
)
from ..config import UPLOADS_DIR, RESULTS_DIR

router = APIRouter(prefix="/api", tags=["detections"])


def _enrich(d: dict) -> dict:
    """Add browser-facing URLs and parsed detection boxes to a raw DB row."""
    d["original_url"] = f"/uploads/{Path(d['original_path']).name}"
    d["annotated_url"] = f"/results/{Path(d['annotated_path']).name}"
    raw = d.get("detections_json", "[]")
    try:
        d["detections"] = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except (ValueError, TypeError):
        d["detections"] = []
    return d


@router.get("/detections")
async def list_detections(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_count: int = Query(None, ge=0),
):
    detections = await get_detections(limit=limit, offset=offset, min_count=min_count)
    detections = [_enrich(d) for d in detections]
    total = await get_total_count()
    return {"data": detections, "total": total, "limit": limit, "offset": offset}


@router.get("/detections/{detection_id}")
async def get_detection(detection_id: int):
    detection = await get_detection_by_id(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return _enrich(detection)


@router.delete("/detections/{detection_id}")
async def delete_detection_record(detection_id: int):
    detection = await get_detection_by_id(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    original_path = Path(detection["original_path"])
    annotated_path = Path(detection["annotated_path"])

    original_path.unlink(missing_ok=True)
    annotated_path.unlink(missing_ok=True)

    await delete_detection(detection_id)
    return {"status": "deleted", "id": detection_id}
