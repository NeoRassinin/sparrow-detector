"""Операции над прямоугольниками на сфере (в первом приближении — плоская геометрия в градусах)."""

from __future__ import annotations

import math
from typing import Iterator

from sparrow_loader.models import BoundingBox


def bbox_from_tuple(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
) -> BoundingBox:
    """Собирает типизированный словарь :class:`BoundingBox` из четырёх чисел.

    Args:
        min_lat: Южная граница.
        max_lat: Северная граница.
        min_lon: Западная граница.
        max_lon: Восточная граница.

    Returns:
        Словарь с ключами ``min_lat``, ``max_lat``, ``min_lon``, ``max_lon``.
    """
    return BoundingBox(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )


def bbox_span_lat(bbox: BoundingBox) -> float:
    """Возвращает протяжённость прямоугольника по широте в градусах.

    Args:
        bbox: Исходный прямоугольник.

    Returns:
        Неотрицательная разность ``max_lat - min_lat``.
    """
    return bbox["max_lat"] - bbox["min_lat"]


def bbox_span_lon(bbox: BoundingBox) -> float:
    """Возвращает протяжённость прямоугольника по долготе в градусах.

    Args:
        bbox: Исходный прямоугольник.

    Returns:
        Неотрицательная разность ``max_lon - min_lon`` (без учёта перехода через 180°).
    """
    return bbox["max_lon"] - bbox["min_lon"]


def bbox_min_edge(bbox: BoundingBox) -> float:
    """Находит длину более короткой стороны прямоугольника в градусах.

    Нужно, чтобы остановить дробление, когда ячейка становится слишком маленькой.

    Args:
        bbox: Исходный прямоугольник.

    Returns:
        Минимум из ширины по широте и ширины по долготе.
    """
    return min(bbox_span_lat(bbox), bbox_span_lon(bbox))


def split_bbox_quarters(bbox: BoundingBox) -> Iterator[BoundingBox]:
    """Делит прямоугольник на четыре равные подобласти (как четыре квадранта).

    Используется для «раскрытия» кластеров: сервер возвращает агрегаты при крупном масштабе,
    а при уменьшении области запроса отдаёт отдельные точки.

    Args:
        bbox: Родительский прямоугольник.

    Yields:
        Ровно четыре дочерних прямоугольника в порядке: ЮЗ, ЮВ, СЗ, СВ
        (юго-западный, юго-восточный, северо-западный, северо-восточный).
    """
    mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2.0
    mid_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2.0
    # Юго-запад
    yield bbox_from_tuple(bbox["min_lat"], mid_lat, bbox["min_lon"], mid_lon)
    # Юго-восток
    yield bbox_from_tuple(bbox["min_lat"], mid_lat, mid_lon, bbox["max_lon"])
    # Северо-запад
    yield bbox_from_tuple(mid_lat, bbox["max_lat"], bbox["min_lon"], mid_lon)
    # Северо-восток
    yield bbox_from_tuple(mid_lat, bbox["max_lat"], mid_lon, bbox["max_lon"])


def split_bbox_halves_shortest_axis(bbox: BoundingBox) -> tuple[BoundingBox, BoundingBox]:
    """Делит прямоугольник на **две** равные части по **более короткой** стороне.

    Если по широте протяжённость меньше либо равна долготной — режем по широте (юг/север);
    иначе — по долготе (запад/восток). Так короткая сторона у потомков уменьшается вдвое
    при **одном** уровне рекурсии и **двух** дочерних запросах вместо четырёх у квадрантов,
    что помогает в узких «стеклах» кластеров без такого же раздува числа ветвей.

    Args:
        bbox: Родительский прямоугольник.

    Returns:
        Пара смежных дочерних прямоугольников (сначала «нижняя/левая» половина, затем «верхняя/правая»).

    Raises:
        ValueError: Если протяжённость по широте или долготе неположительна (вырожденный bbox).
    """
    lat_span = bbox_span_lat(bbox)
    lon_span = bbox_span_lon(bbox)
    if lat_span <= 0 or lon_span <= 0:
        raise ValueError("split_bbox_halves_shortest_axis: вырожденный bbox")
    if lat_span <= lon_span:
        mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2.0
        south = bbox_from_tuple(bbox["min_lat"], mid_lat, bbox["min_lon"], bbox["max_lon"])
        north = bbox_from_tuple(mid_lat, bbox["max_lat"], bbox["min_lon"], bbox["max_lon"])
        return south, north
    mid_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2.0
    west = bbox_from_tuple(bbox["min_lat"], bbox["max_lat"], bbox["min_lon"], mid_lon)
    east = bbox_from_tuple(bbox["min_lat"], bbox["max_lat"], mid_lon, bbox["max_lon"])
    return west, east


def zoom_for_depth(initial_zoom: int, max_zoom: int, depth: int) -> int:
    """Вычисляет параметр ``zoom`` для запроса к API с учётом глубины рекурсии.

    Карта на сайте передаёт больший ``zoom`` при приближении; мы моделируем это
    добавлением ``depth`` к стартовому уровню, не превышая ``max_zoom``.

    Args:
        initial_zoom: Значение ``zoom`` для корневого прямоугольника.
        max_zoom: Верхняя граница.
        depth: Текущая глубина рекурсии (0 — корень).

    Returns:
        Целое значение ``zoom`` в ``[initial_zoom, max_zoom]``.
    """
    return int(min(max_zoom, initial_zoom + depth))


def area_m2_approx(bbox: BoundingBox, latitude_ref: float | None = None) -> float:
    """Грубо оценивает площадь прямоугольника в м² для порядка величины.

    Использует локальное приближение: 1° широты ≈ 111 км; 1° долготы масштабируется
    по ``cos`` средней широты. Точность не геодезическая, достаточна для логов.

    Args:
        bbox: Прямоугольник в градусах.
        latitude_ref: Если задано, используется как средняя широта; иначе берётся середина ``bbox``.

    Returns:
        Площадь в квадратных метрах.
    """
    lat_mid = latitude_ref if latitude_ref is not None else (bbox["min_lat"] + bbox["max_lat"]) / 2.0
    lat_rad = math.radians(lat_mid)
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(lat_rad)
    w_lat = bbox_span_lat(bbox) * meters_per_deg_lat
    w_lon = bbox_span_lon(bbox) * meters_per_deg_lon
    return abs(w_lat * w_lon)
