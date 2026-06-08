"""Объединение двух папок со снимками в одну без дубликатов (для датасетов ML)."""

from __future__ import annotations

import csv
import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, Literal

logger = logging.getLogger(__name__)

#: Расширения файлов, считающихся изображениями при обходе каталогов.
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"},
)

DedupeMode = Literal["name", "hash", "both"]


class DedupeModeEnum(str, Enum):
    """Режим определения дубликата при слиянии двух выгрузок.

    Attributes:
        NAME: Считать дубликатом совпадение **имени файла** (basename), без учёта подпапки.
        HASH: Считать дубликатом совпадение **SHA-256** содержимого файла.
        BOTH: Пропускать файл, если совпало **имя или хэш** (максимально строгий набор для ML).
    """

    NAME = "name"
    HASH = "hash"
    BOTH = "both"


@dataclass(slots=True)
class DedupeRecord:
    """Одна строка журнала операции копирования.

    Attributes:
        action: ``copied`` или ``skipped``.
        source: Абсолютный или исходный путь к файлу в одной из двух папок-источников.
        destination: Путь в целевой папке (пустой, если пропуск).
        reason: Причина пропуска или пустая строка при успешном копировании.
        file_name: Basename файла.
        content_hash: SHA-256 в hex или пусто, если хэш не вычислялся.
    """

    action: str
    source: str
    destination: str
    reason: str
    file_name: str
    content_hash: str = ""


@dataclass
class DedupeStats:
    """Сводка результата слияния двух каталогов.

    Attributes:
        copied: Число скопированных уникальных файлов.
        skipped_by_name: Пропущено из-за уже встреченного имени (режимы ``name`` и ``both``).
        skipped_by_hash: Пропущено из-за уже встреченного хэша (режимы ``hash`` и ``both``).
        errors: Число файлов, которые не удалось обработать.
        records: Подробный журнал операций для отчёта CSV.
    """

    copied: int = 0
    skipped_by_name: int = 0
    skipped_by_hash: int = 0
    errors: int = 0
    records: list[DedupeRecord] = field(default_factory=list)


def iter_image_files(root: Path) -> Iterator[Path]:
    """Рекурсивно перечисляет файлы изображений в каталоге.

    Args:
        root: Корень первой или второй выгрузки (может содержать подкаталог ``images`` и др.).

    Yields:
        Пути к файлам с расширением из :data:`IMAGE_SUFFIXES`.

    Raises:
        FileNotFoundError: Если ``root`` не существует.
    """
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Каталог не найден: {root}")
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def file_sha256(path: Path, chunk_size: int = 65_536) -> str:
    """Вычисляет SHA-256 содержимого файла.

    Args:
        path: Путь к файлу на диске.
        chunk_size: Размер блока чтения в байтах.

    Returns:
        Строка из 64 hex-символов.

    Raises:
        OSError: При ошибке чтения файла.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _should_skip_by_name(file_name: str, seen_names: set[str], mode: DedupeModeEnum) -> bool:
    """Проверяет, нужно ли пропустить файл из-за совпадения basename.

    Args:
        file_name: Имя файла без пути (например ``84064_photo.jpg``).
        seen_names: Множество уже принятых имён.
        mode: Режим дедупликации.

    Returns:
        ``True``, если файл следует пропустить по имени.
    """
    if mode not in (DedupeModeEnum.NAME, DedupeModeEnum.BOTH):
        return False
    return file_name in seen_names


def _should_skip_by_hash(
    content_hash: str,
    seen_hashes: set[str],
    mode: DedupeModeEnum,
) -> bool:
    """Проверяет, нужно ли пропустить файл из-за совпадения хэша содержимого.

    Args:
        content_hash: SHA-256 в hex.
        seen_hashes: Множество уже принятых хэшей.
        mode: Режим дедупликации.

    Returns:
        ``True``, если файл следует пропустить по хэшу.
    """
    if mode not in (DedupeModeEnum.HASH, DedupeModeEnum.BOTH):
        return False
    return content_hash in seen_hashes


def _unique_dest_path(dest_dir: Path, file_name: str, seen_dest_names: set[str]) -> Path:
    """Подбирает путь назначения, избегая перезаписи при редком коллизии имён.

    Если ``file_name`` уже занят в целевом каталоге, добавляет суффикс ``_dupN`` перед расширением.

    Args:
        dest_dir: Каталог назначения.
        file_name: Желаемое имя файла.
        seen_dest_names: Имена, уже зарезервированные в этом прогоне.

    Returns:
        Свободный путь ``dest_dir / имя``.
    """
    candidate = dest_dir / file_name
    if candidate.name not in seen_dest_names and not candidate.exists():
        return candidate
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    n = 1
    while True:
        alt_name = f"{stem}_dup{n}{suffix}"
        alt = dest_dir / alt_name
        if alt.name not in seen_dest_names and not alt.exists():
            return alt
        n += 1


def merge_unique_images(
    src_a: Path,
    src_b: Path,
    dest: Path,
    *,
    mode: DedupeMode = "both",
    compute_hash: bool | None = None,
) -> DedupeStats:
    """Копирует уникальные снимки из двух каталогов в третий.

    Порядок обработки: сначала все файлы из ``src_a``, затем из ``src_b``. При пересечении
    bbox на карте одни и те же анкеты часто дают **одинаковые имена** файлов — режим ``name``
    отсекает повтор; режим ``hash`` отсекает одинаковое содержимое даже при разных именах.

    Args:
        src_a: Первая папка (например, внутренний квадрат выгрузки).
        src_b: Вторая папка (внешний квадрат, включающий первый).
        dest: Целевая папка для уникального датасета (создаётся при необходимости).
        mode: ``name``, ``hash`` или ``both`` (по умолчанию ``both``).
        compute_hash: Явно включить/выключить расчёт SHA-256; по умолчанию включён
            для ``hash`` и ``both``, выключен для ``name``.

    Returns:
        Статистика и список записей :class:`DedupeRecord` для отчёта.
    """
    mode_enum = DedupeModeEnum(mode)
    if compute_hash is None:
        compute_hash = mode_enum in (DedupeModeEnum.HASH, DedupeModeEnum.BOTH)

    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)

    seen_names: set[str] = set()
    seen_hashes: set[str] = set()
    seen_dest_names: set[str] = set()
    stats = DedupeStats()

    for label, root in (("A", src_a), ("B", src_b)):
        logger.info("Обход источника %s: %s", label, root.resolve())
        for source_path in iter_image_files(root):
            file_name = source_path.name.lower()
            content_hash = ""
            try:
                if compute_hash:
                    content_hash = file_sha256(source_path)
            except OSError as exc:
                stats.errors += 1
                stats.records.append(
                    DedupeRecord(
                        action="error",
                        source=str(source_path),
                        destination="",
                        reason=str(exc),
                        file_name=file_name,
                        content_hash="",
                    ),
                )
                logger.warning("Не удалось прочитать %s: %s", source_path, exc)
                continue

            if _should_skip_by_name(file_name, seen_names, mode_enum):
                stats.skipped_by_name += 1
                stats.records.append(
                    DedupeRecord(
                        action="skipped",
                        source=str(source_path),
                        destination="",
                        reason="duplicate_name",
                        file_name=file_name,
                        content_hash=content_hash,
                    ),
                )
                continue

            if content_hash and _should_skip_by_hash(content_hash, seen_hashes, mode_enum):
                stats.skipped_by_hash += 1
                stats.records.append(
                    DedupeRecord(
                        action="skipped",
                        source=str(source_path),
                        destination="",
                        reason="duplicate_hash",
                        file_name=file_name,
                        content_hash=content_hash,
                    ),
                )
                continue

            dest_path = _unique_dest_path(dest, source_path.name, seen_dest_names)
            try:
                shutil.copy2(source_path, dest_path)
            except OSError as exc:
                stats.errors += 1
                stats.records.append(
                    DedupeRecord(
                        action="error",
                        source=str(source_path),
                        destination="",
                        reason=str(exc),
                        file_name=file_name,
                        content_hash=content_hash,
                    ),
                )
                logger.warning("Не удалось скопировать %s: %s", source_path, exc)
                continue

            seen_names.add(file_name)
            if content_hash:
                seen_hashes.add(content_hash)
            seen_dest_names.add(dest_path.name)
            stats.copied += 1
            stats.records.append(
                DedupeRecord(
                    action="copied",
                    source=str(source_path),
                    destination=str(dest_path),
                    reason="",
                    file_name=file_name,
                    content_hash=content_hash,
                ),
            )

    logger.info(
        "Готово: скопировано=%s, пропуск по имени=%s, пропуск по хэшу=%s, ошибок=%s",
        stats.copied,
        stats.skipped_by_name,
        stats.skipped_by_hash,
        stats.errors,
    )
    return stats


def write_dedupe_report(report_path: Path, records: list[DedupeRecord]) -> None:
    """Записывает CSV-отчёт о копировании и пропусках.

    Args:
        report_path: Путь к ``dedupe_report.csv`` (родительский каталог создаётся).
        records: Список :class:`DedupeRecord` из :func:`merge_unique_images`.

    Returns:
        ``None``.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["action", "file_name", "source", "destination", "reason", "content_hash"]
    with report_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "action": rec.action,
                    "file_name": rec.file_name,
                    "source": rec.source,
                    "destination": rec.destination,
                    "reason": rec.reason,
                    "content_hash": rec.content_hash,
                },
            )
    logger.info("Отчёт записан: %s", report_path.resolve())
