"""Рекурсивный обход прямоугольников: раскрытие кластеров и сбор уникальных точек."""

from __future__ import annotations

import logging
from typing import Any

from requests import Session

from sparrow_loader.client import extract_object_list, fetch_objects_raw
from sparrow_loader.config import HarvestSettings
from sparrow_loader.models import BoundingBox, PointRecord
from sparrow_loader.spatial import (
    bbox_min_edge,
    bbox_span_lat,
    bbox_span_lon,
    split_bbox_halves_shortest_axis,
    split_bbox_quarters,
    zoom_for_depth,
)

# Не дробить дальше при численно нулевой стороне (защита от зацикливания).
_MIN_DEG_SPAN: float = 1e-14

logger = logging.getLogger(__name__)


def _harvest_limit_reached(settings: HarvestSettings, out: dict[int, PointRecord]) -> bool:
    """Проверяет, достигнут ли лимит числа собранных точек (режим тестового прогона).

    Args:
        settings: Настройки; используется поле ``max_points``.
        out: Текущий словарь собранных точек.

    Returns:
        ``True``, если ``max_points`` задан и ``len(out) >= max_points``.
    """
    limit = settings.max_points
    return limit is not None and len(out) >= limit


def _is_point_object(obj: dict[str, Any]) -> bool:
    """Проверяет, что словарь описывает наблюдение ``type=point``.

    Args:
        obj: Элемент списка ``objects`` из ответа API.

    Returns:
        ``True``, если поле ``type`` равно строке ``point``.
    """
    return obj.get("type") == "point"


def _is_cluster_object(obj: dict[str, Any]) -> bool:
    """Проверяет, что словарь описывает агрегат ``type=cluster``.

    Args:
        obj: Элемент списка ``objects`` из ответа API.

    Returns:
        ``True``, если поле ``type`` равно строке ``cluster``.
    """
    return obj.get("type") == "cluster"


def parse_point_record(
    obj: dict[str, Any],
    source_bbox: BoundingBox,
) -> PointRecord | None:
    """Преобразует сырой объект ``point`` в :class:`PointRecord`.

    Отбрасывает записи без числового ``id`` или с неожиданным типом.

    Args:
        obj: Словарь одной точки из API.
        source_bbox: Прямоугольник HTTP-запроса, в ответе на который пришла точка.

    Returns:
        Заполненная :class:`PointRecord` или ``None``, если объект не подходит.
    """
    if not _is_point_object(obj):
        return None
    pid = obj.get("id")
    if not isinstance(pid, int):
        return None
    action_id = obj.get("action_id")
    if not isinstance(action_id, int):
        action_id = 0
    region = obj.get("region")
    if not isinstance(region, str):
        region = ""
    lat = obj.get("lat")
    lon = obj.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    sparrows = obj.get("sparrows")
    if not isinstance(sparrows, int):
        sparrows = int(sparrows) if isinstance(sparrows, (int, float)) else 0
    image_url = obj.get("image_url")
    if image_url is None:
        image_url = ""
    elif not isinstance(image_url, str):
        image_url = str(image_url)
    return PointRecord(
        point_id=pid,
        action_id=action_id,
        region=region,
        lat=float(lat),
        lon=float(lon),
        sparrows=sparrows,
        image_url=image_url,
        source_bbox=dict(source_bbox),
        raw=dict(obj),
    )


def collect_points_recursive(
    session: Session,
    settings: HarvestSettings,
    bbox: BoundingBox,
    depth: int,
    seen_ids: set[int],
    out: dict[int, PointRecord],
) -> None:
    """Рекурсивно обходит прямоугольник: запрашивает объекты и дробит область при наличии кластеров.

    Алгоритм:

    #. Если короткая сторона ячейки уже меньше ``min_bbox_size_deg``, **всё равно** выполнить
       запрос к API (раньше такие ячейки отбрасывались и кластеры не раскрывались).
    #. Все ``point`` нормализовать и положить в ``out`` (ключ — ``id``), пропуская уже виденные.
    #. При ``cluster`` в ответе и не исчерпанной ``max_depth``:
       - в обычной ячейке (достаточно крупной) — деление на **4 квадранта**;
       - если ячейка была «слишком мелкой» до запроса — **альтернативная стратегия**:
         деление **пополам по короткой стороне** (2 полосы), чтобы уменьшить ветвление при той же
         геометрической мелкости вдоль узкого измерения.

    Args:
        session: Открытая HTTP-сессия.
        settings: Полный набор параметров прогона.
        bbox: Текущий прямоугольник.
        depth: Текущая глубина рекурсии (0 — корень).
        seen_ids: Множество уже встреченных числовых ``id`` точек (для дедупликации).
        out: Словарь `id -> PointRecord`; обновляется по ссылке.

    Returns:
        ``None``; результат накапливается в ``out``.
    """
    if _harvest_limit_reached(settings, out):
        return

    if bbox_span_lat(bbox) < _MIN_DEG_SPAN or bbox_span_lon(bbox) < _MIN_DEG_SPAN:
        logger.warning("Вырожденный bbox (нулевая сторона), пропуск: %s depth=%s", bbox, depth)
        return

    min_edge = bbox_min_edge(bbox)
    undersized_before_fetch = min_edge < settings.min_bbox_size_deg
    if undersized_before_fetch:
        logger.info(
            "Ячейка меньше min_bbox_size (%s°); запрос и при кластерах — деление пополам по короткой стороне: "
            "bbox=%s depth=%s",
            settings.min_bbox_size_deg,
            bbox,
            depth,
        )

    z = zoom_for_depth(settings.initial_zoom, settings.max_zoom, depth)
    payload = fetch_objects_raw(session, settings, bbox, z)
    items = extract_object_list(payload)

    clusters_present = any(_is_cluster_object(o) for o in items)
    for obj in items:
        if not _is_point_object(obj):
            continue
        rec = parse_point_record(obj, bbox)
        if rec is None:
            continue
        if rec.point_id in seen_ids:
            continue
        seen_ids.add(rec.point_id)
        out[rec.point_id] = rec
        if _harvest_limit_reached(settings, out):
            return

    if not clusters_present:
        return

    if _harvest_limit_reached(settings, out):
        return

    if depth >= settings.max_depth:
        logger.warning(
            "Достигнута max_depth=%s при наличии кластеров в bbox=%s — возможна потеря детализации",
            settings.max_depth,
            bbox,
        )
        return

    if undersized_before_fetch:
        try:
            half_a, half_b = split_bbox_halves_shortest_axis(bbox)
        except ValueError:
            logger.warning("Не удалось разбить bbox пополам: %s depth=%s", bbox, depth)
            return
        for sub in (half_a, half_b):
            collect_points_recursive(session, settings, sub, depth + 1, seen_ids, out)
        return

    for sub in split_bbox_quarters(bbox):
        collect_points_recursive(session, settings, sub, depth + 1, seen_ids, out)


def harvest_all_points(
    session: Session,
    settings: HarvestSettings,
) -> dict[int, PointRecord]:
    """Точка входа: запускает рекурсивный сбор, начиная с ``settings.bbox``.

    Args:
        session: Настроенная HTTP-сессия.
        settings: Параметры области, сезонов и ограничений обхода.

    Returns:
        Словарь ``point_id -> PointRecord`` по всем уникальным точкам, найденным в процессе.
    """
    bbox: BoundingBox = {
        "min_lat": settings.bbox[0],
        "max_lat": settings.bbox[1],
        "min_lon": settings.bbox[2],
        "max_lon": settings.bbox[3],
    }
    seen: set[int] = set()
    out: dict[int, PointRecord] = {}
    collect_points_recursive(session, settings, bbox, 0, seen, out)
    logger.info("Собрано уникальных точек: %s", len(out))
    return out
