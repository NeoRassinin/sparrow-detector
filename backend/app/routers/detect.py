import uuid
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
import traceback

from ..config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE, UPLOADS_DIR, RESULTS_DIR
from ..services.yolo import run_inference, save_annotated
from ..models.database import insert_detection

router = APIRouter(prefix="/api", tags=["detect"])


@router.post("/detect")
async def detect(file: UploadFile = File(...), patch: bool = Form(False)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = "." + (file.filename.split(".")[-1].lower() if "." in file.filename else "jpg")
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        image = Image.open(BytesIO(contents))
        image_width, image_height = image.size
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file")

    file_id = str(uuid.uuid4())
    original_filename = f"{file_id}{file_ext}"
    original_path = UPLOADS_DIR / original_filename
    annotated_filename = f"{file_id}_annotated.jpg"
    annotated_path = RESULTS_DIR / annotated_filename

    original_path.write_bytes(contents)

    start_time = time.time()
    try:
        detections, annotated_im, sparrow_count = run_inference(
            original_path, use_patches=patch
        )
    except Exception as e:
        original_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")

    processing_time = (time.time() - start_time) * 1000

    save_annotated(annotated_im, annotated_path)

    db_id = await insert_detection(
        filename=original_filename,
        original_path=str(original_path),
        annotated_path=str(annotated_path),
        sparrow_count=sparrow_count,
        detections=detections,
        processing_time_ms=processing_time,
        image_width=image_width,
        image_height=image_height,
    )

    return {
        "id": db_id,
        "timestamp": None,
        "filename": original_filename,
        "original_url": f"/uploads/{original_filename}",
        "annotated_url": f"/results/{annotated_filename}",
        "sparrow_count": sparrow_count,
        "detections": detections,
        "processing_time_ms": round(processing_time, 2),
        "image_width": image_width,
        "image_height": image_height,
        "mode": "patch" if patch else "standard",
    }
