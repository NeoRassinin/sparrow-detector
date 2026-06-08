"""HTTP-клиент для эндпоинта ``/api/objects``: параметры запроса, парсинг JSON, повторы при сбоях."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests import Response, Session

from sparrow_loader.config import DEFAULT_USER_AGENT, HarvestSettings
from sparrow_loader.models import BoundingBox

logger = logging.getLogger(__name__)


def build_session(settings: HarvestSettings) -> Session:
    """Создаёт ``requests.Session`` с заголовками по умолчанию.

    Сессия переиспользует TCP-соединение к ``sparrow.over.ru``, что уменьшает накладные расходы
    при серии запросов.

    Args:
        settings: Настройки прогона; используются таймауты и User-Agent (через константу в конфиге).

    Returns:
        Настроенный экземпляр ``requests.Session``.
    """
    session = Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
    )
    return session


def build_query_params(
    bbox: BoundingBox,
    zoom: int,
    season_ids: tuple[int, ...],
    region: str | None,
) -> dict[str, str | int | float]:
    """Формирует словарь query-параметров для GET ``/api/objects``.

    Соответствует тому, что отправляет карта: границы видимой области, уровень масштаба,
    список сезонов и опционально название субъекта.

    Args:
        bbox: Прямоугольник ``min_lat``, ``max_lat``, ``min_lon``, ``max_lon``.
        zoom: Уровень масштаба (целое число, как в URL карты).
        season_ids: Кортеж идентификаторов акций; в строку запроса сериализуется через запятую.
        region: Если не ``None``, добавляется фильтр по названию региона (как в UI).

    Returns:
        Плоский словарь для ``params=`` в ``requests.get``.
    """
    seasons_str = ",".join(str(sid) for sid in season_ids)
    params: dict[str, str | int | float] = {
        "zoom": zoom,
        "min_lat": bbox["min_lat"],
        "max_lat": bbox["max_lat"],
        "min_lon": bbox["min_lon"],
        "max_lon": bbox["max_lon"],
        "seasons": seasons_str,
    }
    if region is not None and region.strip():
        params["region"] = region.strip()
    return params


def fetch_objects_raw(
    session: Session,
    settings: HarvestSettings,
    bbox: BoundingBox,
    zoom: int,
) -> dict[str, Any]:
    """Загружает и разбирает JSON ответа ``/api/objects`` для одной ячейки карты.

    Выполняет повторные попытки при временных ошибках сети и ответах 5xx с экспоненциальной
    задержкой между попытками.

    Args:
        session: Открытая HTTP-сессия.
        settings: Параметры таймаутов, задержки между запросами и числа повторов.
        bbox: Прямоугольник запроса.
        zoom: Уровень масштаба для параметра ``zoom``.

    Returns:
        Распарсенный корневой объект JSON (ожидается ключ ``objects`` со списком).

    Raises:
        requests.HTTPError: Если после всех повторов статус не успешный.
        ValueError: Если тело ответа не является JSON-объектом.
    """
    params = build_query_params(bbox, zoom, settings.season_ids, settings.region)
    last_exc: Exception | None = None
    for attempt in range(1, settings.max_retries + 1):
        try:
            if settings.request_delay_sec > 0:
                time.sleep(settings.request_delay_sec)
            response: Response = session.get(
                settings.api_url,
                params=params,
                timeout=(settings.connect_timeout_sec, settings.read_timeout_sec),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Ожидался JSON-объект с корнем dict")
            return data
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            logger.warning(
                "Попытка %s/%s не удалась для bbox=%s zoom=%s: %s",
                attempt,
                settings.max_retries,
                bbox,
                zoom,
                exc,
            )
            if attempt < settings.max_retries:
                time.sleep(0.5 * attempt)
    assert last_exc is not None
    raise last_exc


def extract_object_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Извлекает список ``objects`` из корня ответа API.

    Args:
        payload: Распарсенный JSON.

    Returns:
        Список словарей объектов; пустой список, если ключа нет или тип не список.
    """
    raw = payload.get("objects")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]
