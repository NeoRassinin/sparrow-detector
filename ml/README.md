# ML tools

## Auto annotation

Generate YOLO pseudo-labels for new raw images:

```bash
python ml/auto_annotate.py \
  --weights backend/weights/best.pt \
  --source data/raw/mkad_batch/images \
  --project data/raw/mkad_batch \
  --name pred_annot \
  --conf 0.15 \
  --device 0
```

## FiftyOne inspection
Open validation split with model predictions:

```bash
python ml/fiftyone_inspect.py \
  --dataset-dir dataset/My_Jack_sparrow_yolo_v1 \
  --weights backend/weights/best.pt \
  --split val \
  --overwrite
```