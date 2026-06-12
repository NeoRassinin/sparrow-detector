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
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", 0.5))

# Patch-based ("tiled") inference — opt-in mode for far-plane / small / dense
# birds. The image is split into overlapping tiles, the model runs on each at
# near-native resolution, and detections are merged back together.
PATCH_SHAPE_X = int(os.getenv("PATCH_SHAPE_X", 640))
PATCH_SHAPE_Y = int(os.getenv("PATCH_SHAPE_Y", 640))
PATCH_OVERLAP_X = int(os.getenv("PATCH_OVERLAP_X", 25))
PATCH_OVERLAP_Y = int(os.getenv("PATCH_OVERLAP_Y", 25))
PATCH_NMS_THRESHOLD = float(os.getenv("PATCH_NMS_THRESHOLD", 0.25))
PATCH_MATCH_METRIC = os.getenv("PATCH_MATCH_METRIC", "IOS")
# Tiles upscale noisy background and hallucinate low-confidence birds, so the
# per-tile pass uses a stricter threshold than the full-image pass.
PATCH_CONFIDENCE_THRESHOLD = float(os.getenv("PATCH_CONFIDENCE_THRESHOLD", 0.5))
# IoU used to dedupe the merged (full-image + tiles) detections.
PATCH_MERGE_IOU = float(os.getenv("PATCH_MERGE_IOU", 0.5))
