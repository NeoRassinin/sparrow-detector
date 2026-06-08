"""Типы данных для геометрии, сырых ответов API и нормализованных записей точек."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


class BoundingBox(TypedDict):
    """Прямоугольная область на карте в градусах WGS84.

    Attributes:
        min_lat: Южная граница (минимальная широта).
        max_lat: Северная граница (максимальная широта).
        min_lon: Западная граница (минимальная долгота).
        max_lon: Восточная граница (максимальная долгота).
    """

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


@dataclass(slots=True)
class PointRecord:
    """Нормализованная запись об одном наблюдении ``type=point``.

    Используется для дедупликации, экспорта в CSV/JSON и сопоставления с локальным файлом снимка.

    Attributes:
        point_id: Уникальный числовой ``id`` точки в базе проекта.
        action_id: Идентификатор сезона (акции).
        region: Название региона из API.
        lat: Широта.
        lon: Долгота.
        sparrows: Число воробьёв.
        image_url: Исходный URL изображения; может быть пустым.
        image_path: Относительный путь к сохранённому файлу внутри ``output_dir`` или ``None``.
        source_bbox: Прямоугольник запроса, из которого получена точка (для отладки).
        raw: Сырой словарь объекта из API (для расширения без поломки схемы).
    """

    point_id: int
    action_id: int
    region: str
    lat: float
    lon: float
    sparrows: int
    image_url: str
    image_path: str | None = None
    source_bbox: BoundingBox | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_csv_row(self) -> dict[str, Any]:
        """Преобразует запись в плоский словарь для записи строки CSV.

        Returns:
            Словарь с ключами-строками и значениями, пригодными для ``csv.DictWriter``.
        """
        return {
            "id": self.point_id,
            "action_id": self.action_id,
            "region": self.region,
            "lat": self.lat,
            "lon": self.lon,
            "sparrows": self.sparrows,
            "image_url": self.image_url,
            "image_path": self.image_path or "",
        }

    def to_json_dict(self) -> dict[str, Any]:
        """Преобразует запись в JSON-совместимый словарь.

        Returns:
            Словарь с метаданными и необязательным ``raw`` для полноты.
        """
        base: dict[str, Any] = {
            "id": self.point_id,
            "action_id": self.action_id,
            "region": self.region,
            "lat": self.lat,
            "lon": self.lon,
            "sparrows": self.sparrows,
            "image_url": self.image_url,
            "image_path": self.image_path,
        }
        if self.source_bbox is not None:
            base["source_bbox"] = dict(self.source_bbox)
        if self.raw:
            base["raw"] = self.raw
        return base
