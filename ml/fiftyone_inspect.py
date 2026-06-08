from pathlib import Path
import argparse

import fiftyone as fo
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect YOLO dataset with FiftyOne")
    parser.add_argument("--dataset-name", default="sparrow_yolo")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--weights", type=Path, default=Path("backend/weights/best.pt"))
    parser.add_argument("--label-field", default="predictions")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.overwrite and args.dataset_name in fo.list_datasets():
        fo.delete_dataset(args.dataset_name)

    dataset = fo.Dataset.from_dir(
        dataset_dir=str(args.dataset_dir),
        dataset_type=fo.types.YOLOv5Dataset,
        split=args.split,
        name=args.dataset_name,
        yaml_path=str(args.dataset_dir / "data.yaml"),
    )

    print(f"Loaded images: {len(dataset)}")
    print(f"Classes: {dataset.default_classes}")

    model = YOLO(str(args.weights))
    dataset.apply_model(model, label_field=args.label_field)

    session = fo.launch_app(dataset)
    session.wait()


if __name__ == "__main__":
    main()