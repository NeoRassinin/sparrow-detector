"""CLI: слияние двух папок со снимками в одну без дубликатов."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sparrow_loader.dedupe import merge_unique_images, write_dedupe_report
from sparrow_loader.logging_config import configure_logging

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов для ``vorobey-dedupe``.

    Returns:
        Настроенный :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="vorobey-dedupe",
        description=(
            "Скопировать уникальные снимки из двух папок (например, внутренний и внешний bbox) "
            "в третью — без дубликатов по имени файла и/или по SHA-256 содержимого."
        ),
    )
    parser.add_argument(
        "src_a",
        type=Path,
        help="Первая папка-источник (обрабатывается раньше; обычно «внутренний» квадрат)",
    )
    parser.add_argument(
        "src_b",
        type=Path,
        help="Вторая папка-источник (обычно «внешний» квадрат, перекрывающий первый)",
    )
    parser.add_argument(
        "dest",
        type=Path,
        help="Целевая папка для уникального набора снимков",
    )
    parser.add_argument(
        "--mode",
        choices=("name", "hash", "both"),
        default="both",
        help=(
            "name — только одинаковые имена файлов; "
            "hash — только одинаковое содержимое; "
            "both — пропуск при совпадении имени ИЛИ хэша (рекомендуется для ML)"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Путь к CSV-отчёту (по умолчанию: DEST/dedupe_report.csv)",
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        help="Не вычислять SHA-256 (эквивалентно --mode name, но явно)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Дублировать лог в stderr",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Уровень DEBUG в журнале",
    )
    return parser


def run_from_args(args: argparse.Namespace) -> int:
    """Выполняет слияние по разобранным аргументам.

    Args:
        args: Результат :meth:`argparse.ArgumentParser.parse_args`.

    Returns:
        Код выхода: ``0`` при успехе, ``1`` при ошибках обработки файлов.
    """
    dest = args.dest.resolve()
    log_path = dest / "dedupe.log"
    configure_logging(log_path, console=args.console, verbose=args.verbose)
    print(f"Журнал: {log_path}", file=sys.stdout)

    mode = "name" if args.no_hash else args.mode
    report_path = args.report if args.report is not None else dest / "dedupe_report.csv"

    logger.info("Режим: %s", mode)
    logger.info("Источник A: %s", args.src_a.resolve())
    logger.info("Источник B: %s", args.src_b.resolve())
    logger.info("Назначение: %s", dest)

    stats = merge_unique_images(args.src_a, args.src_b, dest, mode=mode)
    write_dedupe_report(report_path, stats.records)

    print(
        f"Итог: скопировано={stats.copied}, "
        f"пропуск_имя={stats.skipped_by_name}, "
        f"пропуск_хэш={stats.skipped_by_hash}, "
        f"ошибок={stats.errors}, каталог={dest}",
        file=sys.stdout,
    )
    return 1 if stats.errors else 0


def main() -> None:
    """Точка входа консольной команды ``vorobey-dedupe``.

    Raises:
        SystemExit: С кодом возврата из :func:`run_from_args`.
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    raise SystemExit(run_from_args(args))


if __name__ == "__main__":
    main()
