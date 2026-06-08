from pathlib import Path
import argparse
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-annotate images with YOLO model")
    parser.add_argument("--weights", type=Path, default=Path("backend/weights/best.pt"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=Path("data/auto_annotate"))
    parser.add_argument("--name", type=str, default="pred_annot")
    parser.add_argument("--conf", type=float, default=0.15)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()

    model = YOLO(str(args.weights))
    model.predict(
        source=str(args.source),
        save_txt=True,
        save_conf=False,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        agnostic_nms=False,
        device=args.device,
        project=str(args.project),
        name=args.name,
    )


if __name__ == "__main__":
    main()