"""Сохранение таблицы метаданных в CSV и JSON на диск."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable

from sparrow_loader.models import PointRecord

logger = logging.getLogger(__name__)


def ensure_output_dir(path: Path) -> None:
    """Создаёт каталог назначения, если он ещё не существует.

    Args:
        path: Путь к каталогу (не к файлу).

    Returns:
        ``None``.
    """
    path.mkdir(parents=True, exist_ok=True)


def write_points_csv(records: Iterable[PointRecord], file_path: Path) -> None:
    """Записывает все записи в UTF-8 CSV с заголовком.

    Колонки: ``id``, ``action_id``, ``region``, ``lat``, ``lon``, ``sparrows``, ``image_url``, ``image_path``.

    Args:
        records: Итератор по :class:`PointRecord` (обычно значения словаря ``id -> record``).
        file_path: Путь к файлу ``metadata.csv`` (родительский каталог должен существовать или будет создан).

    Returns:
        ``None``.
    """
    rows = sorted(records, key=lambda r: r.point_id)
    fieldnames = [
        "id",
        "action_id",
        "region",
        "lat",
        "lon",
        "sparrows",
        "image_url",
        "image_path",
    ]
    ensure_output_dir(file_path.parent)
    with file_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in rows:
            writer.writerow(rec.to_csv_row())
    logger.info("Записан CSV: %s строк в %s", len(rows), file_path)


def write_points_json(records: Iterable[PointRecord], file_path: Path) -> None:
    """Сохраняет метаданные в JSON-массив с отступами для читаемости.

    Args:
        records: Набор записей точек.
        file_path: Путь к ``metadata.json``.

    Returns:
        ``None``.
    """
    rows = sorted(records, key=lambda r: r.point_id)
    payload: list[dict[str, Any]] = [rec.to_json_dict() for rec in rows]
    ensure_output_dir(file_path.parent)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    logger.info("Записан JSON: %s записей в %s", len(rows), file_path)
