import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = os.getenv("MODEL_PATH", BASE_DIR / "weights" / "best.pt")
DB_PATH = os.getenv("DB_PATH", BASE_DIR / "db" / "sparrow.db")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", BASE_DIR / "uploads")
RESULTS_DIR = os.getenv("RESULTS_DIR", BASE_DIR / "results")

UPLOADS_DIR = Path(UPLOADS_DIR)
RESULTS_DIR = Path(RESULTS_DIR)
DB_PATH = Path(DB_PATH)

UPLOADS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
DB_PATH.parent.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
MAX_IMAGE_SIZE = 50 * 1024 * 1024
CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.5
