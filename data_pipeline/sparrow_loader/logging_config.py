"""Настройка стандартного модуля :mod:`logging` для CLI (файл ± консоль)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(
    log_file: Path,
    *,
    console: bool = False,
    verbose: bool = False,
    console_min_level: int = logging.WARNING,
) -> None:
    """Подключает обработчики к корневому логгеру: основной вывод в файл, опционально в stderr.

    В корневой логгер **удаляются** прежние обработчики, чтобы при повторном вызове в одном процессе
    не дублировать запись (типично для тестов).

    **Уровни.** В файл пишутся сообщения от ``INFO`` (или ``DEBUG`` при ``verbose=True``). На консоль
    (если включена) по умолчанию идут только ``WARNING`` и выше — чтобы не смешивать поток с
    полным журналом; при ``verbose`` и ``console=True`` порог консоли снижается до ``DEBUG``.

    Args:
        log_file: Путь к UTF-8 файлу журнала. Родительский каталог создаётся при необходимости.
        console: Если ``True``, дублировать записи в ``stderr`` через :class:`logging.StreamHandler`.
        verbose: Если ``True``, порог для файла — ``DEBUG``; иначе ``INFO``.
        console_min_level: Минимальный уровень для консоли при ``verbose=False``
            (по умолчанию только предупреждения и ошибки).

    Returns:
        ``None``.
    """
    root = logging.getLogger()
    root.handlers.clear()
    file_level = logging.DEBUG if verbose else logging.INFO
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log_file = log_file.resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    if console:
        stream = logging.StreamHandler(sys.stderr)
        stream_level = logging.DEBUG if verbose else console_min_level
        stream.setLevel(stream_level)
        stream.setFormatter(fmt)
        root.addHandler(stream)
