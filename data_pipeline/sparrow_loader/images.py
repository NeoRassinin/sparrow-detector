"""Параллельная загрузка файлов снимков по URL из поля ``image_url``."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from sparrow_loader.config import DEFAULT_USER_AGENT, HarvestSettings
from sparrow_loader.models import PointRecord

logger = logging.getLogger(__name__)


def build_local_image_relative_path(
    images_subdir: str,
    point_id: int,
    image_url: str,
) -> str:
    """Строит относительный путь для сохранения файла внутри каталога выгрузки.

    Имя файла: ``{id}_`` + последний сегмент пути из URL (после декодирования percent-encoding).
    Если из URL имя извлечь нельзя, используется ``{id}.jpg``.

    Args:
        images_subdir: Имя подкаталога внутри корня выгрузки (например ``images``).
        point_id: Числовой идентификатор точки.
        image_url: Абсолютный URL изображения.

    Returns:
        Относительный путь с прямыми слэшами (для записи в CSV), например ``images/84064_dscn5269.jpg``.
    """
    parsed = urlparse(image_url)
    tail = Path(unquote(parsed.path)).name
    if not tail or tail in (".", ".."):
        tail = f"{point_id}.jpg"
    else:
        tail = f"{point_id}_{tail}"
    return str(Path(images_subdir) / tail)


def download_single_image(
    settings: HarvestSettings,
    record: PointRecord,
    output_dir: Path,
) -> PointRecord:
    """Скачивает один файл по ``record.image_url`` и проставляет ``image_path``.

    Использует отдельный HTTP GET (без общей :class:`~requests.Session`) для безопасности
    при вызове из пула потоков.

    При пустом URL или ошибке загрузки поле ``image_path`` остаётся ``None``.

    Args:
        settings: Используются ``connect_timeout_sec``, ``image_read_timeout_sec``, ``max_retries``,
            ``images_subdir``.
        record: Запись точки.
        output_dir: Корень выгрузки; файл пишется по пути ``output_dir / относительный_путь``.

    Returns:
        Новая :class:`PointRecord` с заполненным ``image_path`` при успехе.
    """
    url = (record.image_url or "").strip()
    if not url:
        return record

    rel = build_local_image_relative_path(settings.images_subdir, record.point_id, url)
    dest = output_dir / rel
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    timeout = (settings.connect_timeout_sec, settings.image_read_timeout_sec)

    last_exc: requests.RequestException | None = None
    for attempt in range(1, settings.max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                stream=True,
            )
            response.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=65_536):
                    if chunk:
                        fh.write(chunk)
            last_exc = None
            break
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Попытка %s/%s загрузки id=%s: %s",
                attempt,
                settings.max_retries,
                record.point_id,
                exc,
            )
            if attempt < settings.max_retries:
                time.sleep(0.5 * attempt)

    if last_exc is not None:
        logger.warning(
            "Не удалось скачать id=%s url=%s после %s попыток: %s",
            record.point_id,
            url,
            settings.max_retries,
            last_exc,
        )
        return record

    return PointRecord(
        point_id=record.point_id,
        action_id=record.action_id,
        region=record.region,
        lat=record.lat,
        lon=record.lon,
        sparrows=record.sparrows,
        image_url=record.image_url,
        image_path=rel.replace("\\", "/"),
        source_bbox=record.source_bbox,
        raw=record.raw,
    )


def download_images_parallel(
    settings: HarvestSettings,
    records: dict[int, PointRecord],
    output_dir: Path,
) -> dict[int, PointRecord]:
    """Загружает изображения для всех записей с непустым ``image_url`` в пуле потоков.

    Каждая задача вызывает :func:`download_single_image` с собственным HTTP-запросом,
    чтобы не разделять :class:`~requests.Session` между потоками.

    Args:
        settings: Параметры таймаутов и ``max_image_workers``.
        records: Словарь ``id -> PointRecord`` после этапа сбора API.
        output_dir: Корневой каталог выгрузки (создаётся подкаталог ``images``).

    Returns:
        Новый словарь записей с проставленными ``image_path`` там, где загрузка удалась.
    """
    images_root = output_dir / settings.images_subdir
    images_root.mkdir(parents=True, exist_ok=True)

    with_url = [r for r in records.values() if (r.image_url or "").strip()]
    with_url.sort(key=lambda r: r.point_id)
    limit = settings.max_downloads
    if limit is not None and limit > 0:
        logger.info(
            "Ограничение загрузки снимков: скачаем не более %s файлов (записей с непустым URL: %s)",
            limit,
            len(with_url),
        )
        items = with_url[:limit]
    else:
        items = with_url
    if not items:
        return dict(records)

    updated: dict[int, PointRecord] = dict(records)
    workers = max(1, settings.max_image_workers)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(download_single_image, settings, rec, output_dir): rec.point_id
            for rec in items
        }
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                new_rec = fut.result()
                updated[new_rec.point_id] = new_rec
            except Exception as exc:  # pragma: no cover - защита от неожиданных сбоев
                logger.exception("Сбой задачи загрузки id=%s: %s", pid, exc)

    return updated
