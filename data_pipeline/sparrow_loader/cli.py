"""Интерфейс командной строки: разбор аргументов, запуск сбора и выгрузки."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sparrow_loader.client import build_session
from sparrow_loader.config import (
    API_OBJECTS_URL,
    DEFAULT_SEASON_IDS,
    RUSSIA_BBOX,
    HarvestSettings,
)
from sparrow_loader.export import write_points_csv, write_points_json
from sparrow_loader.harvest import harvest_all_points
from sparrow_loader.images import download_images_parallel
from sparrow_loader.logging_config import configure_logging

logger = logging.getLogger(__name__)


def parse_season_ids(value: str) -> tuple[int, ...]:
    """Преобразует строку со списком идентификаторов сезонов в кортеж целых чисел.

    Формат входа: числа, разделённые запятой, без пробелов или с пробелами
    (например ``40, 20561 , 27123``).

    Args:
        value: Строка из аргумента командной строки ``--seasons``.

    Returns:
        Кортеж идентификаторов акций в порядке перечисления.

    Raises:
        argparse.ArgumentTypeError: Если строка пуста или содержит нечисловые фрагменты.
    """
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("Список сезонов не должен быть пустым")
    try:
        return tuple(int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Ожидались целые числа в --seasons: {exc}") from exc


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """Парсит строку ``min_lat,max_lat,min_lon,max_lon`` в четвёрку float.

    Args:
        value: Четыре числа через запятую в указанном порядке (градусы WGS84).

    Returns:
        Кортеж ``(min_lat, max_lat, min_lon, max_lon)``.

    Raises:
        argparse.ArgumentTypeError: При неверном числе полей или нечисловых значениях.
    """
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "Ожидалось ровно 4 числа: min_lat,max_lat,min_lon,max_lon",
        )
    try:
        nums = tuple(float(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Нечисловые значения в --bbox: {exc}") from exc
    min_lat, max_lat, min_lon, max_lon = nums
    if min_lat >= max_lat or min_lon >= max_lon:
        raise argparse.ArgumentTypeError(
            "Нужно min_lat < max_lat и min_lon < max_lon",
        )
    return nums


def build_arg_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов CLI с описанием всех опций.

    Returns:
        Настроенный :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="sparrow-fetch",
        description=(
            "Выгрузка точек переписи воробьёв через API sparrow.over.ru "
            "(карта map.vorobey.nbud.ru): рекурсивный обход области, метаданные и снимки."
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("sparrow_out"),
        help="Каталог для metadata.csv, metadata.json и подкаталога с изображениями (по умолчанию: sparrow_out)",
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        default=None,
        help=(
            "Границы области: min_lat,max_lat,min_lon,max_lon в градусах. "
            f"По умолчанию — охват РФ {RUSSIA_BBOX}"
        ),
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Необязательный фильтр: название субъекта РФ, как в выпадающем списке на карте",
    )
    parser.add_argument(
        "--seasons",
        type=parse_season_ids,
        default=DEFAULT_SEASON_IDS,
        help=f"Идентификаторы акций через запятую (по умолчанию: {','.join(map(str, DEFAULT_SEASON_IDS))})",
    )
    parser.add_argument(
        "--initial-zoom",
        type=int,
        default=6,
        help="Начальный параметр zoom для API (корень рекурсии)",
    )
    parser.add_argument(
        "--max-zoom",
        type=int,
        default=16,
        help="Верхняя граница zoom при углублении",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=14,
        help="Максимальное число последовательных делений прямоугольника пополам по широте/долготе",
    )
    parser.add_argument(
        "--min-bbox-size",
        type=float,
        default=0.002,
        help="Минимальный размер стороны ячейки в градусах; ниже — остановка с предупреждением",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Пауза в секундах между запросами к API (снижает риск ограничений)",
    )
    parser.add_argument(
        "--image-workers",
        type=int,
        default=2,
        help="Число параллельных загрузок изображений (меньше — мягче для сервера снимков)",
    )
    parser.add_argument(
        "--image-read-timeout",
        type=float,
        default=120.0,
        metavar="SEC",
        help="Таймаут чтения одного файла снимка в секундах",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Только собрать метаданные через API, не скачивать файлы снимков",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=None,
        metavar="N",
        help="Остановить сбор API после N уникальных точек (тестовый режим)",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=None,
        metavar="N",
        help="Скачать не более N файлов с непустым image_url (остальные строки в CSV без файла)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Путь к файлу журнала UTF-8 (по умолчанию: OUTPUT_DIR/sparrow_fetch.log)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Дополнительно дублировать журнал в stderr (по умолчанию только файл)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Переопределить URL эндпоинта /api/objects (редко нужно)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="В файл (и при --console в терминал) писать уровень DEBUG",
    )
    return parser


def run_from_args(args: argparse.Namespace) -> int:
    """Выполняет полный цикл: сбор точек, опционально снимки, запись CSV/JSON.

    Args:
        args: Результат :func:`argparse.ArgumentParser.parse_args`.

    Returns:
        Код выхода процесса: ``0`` при успехе.
    """
    out_dir = args.output_dir.resolve()
    log_path = args.log_file if args.log_file is not None else out_dir / "sparrow_fetch.log"
    configure_logging(log_path, console=args.console, verbose=args.verbose)
    print(f"Журнал выполнения: {log_path}", file=sys.stdout)

    bbox = args.bbox if args.bbox is not None else RUSSIA_BBOX
    settings = HarvestSettings(
        api_url=args.api_url or API_OBJECTS_URL,
        season_ids=args.seasons,
        bbox=bbox,
        initial_zoom=args.initial_zoom,
        max_zoom=args.max_zoom,
        max_depth=args.max_depth,
        min_bbox_size_deg=args.min_bbox_size,
        request_delay_sec=args.delay,
        region=args.region,
        output_dir=args.output_dir,
        max_image_workers=args.image_workers,
        max_points=args.max_points,
        max_downloads=args.max_downloads,
        image_read_timeout_sec=args.image_read_timeout,
    )

    logger.info("Каталог выгрузки: %s", out_dir)
    logger.info("Сезоны (action ids): %s", ",".join(map(str, settings.season_ids)))
    logger.info("Область bbox: %s", settings.bbox)
    if settings.max_points is not None:
        logger.info("Лимит точек (тест): %s", settings.max_points)
    if settings.max_downloads is not None:
        logger.info("Лимит загрузок снимков: %s", settings.max_downloads)

    session = build_session(settings)
    points = harvest_all_points(session, settings)

    if not args.no_images:
        points = download_images_parallel(settings, points, out_dir)

    csv_path = out_dir / "metadata.csv"
    json_path = out_dir / "metadata.json"
    write_points_csv(points.values(), csv_path)
    write_points_json(points.values(), json_path)

    images_dir = (out_dir / settings.images_subdir).resolve()
    n_saved = sum(1 for r in points.values() if r.image_path)
    n_with_url = sum(1 for r in points.values() if (r.image_url or "").strip())
    logger.info("Итог: точек в выгрузке %s; с непустым image_url: %s; файлов снимков сохранено: %s", len(points), n_with_url, n_saved)
    logger.info("Снимки (если скачивались): каталог %s", images_dir)
    logger.info("Таблицы: %s и %s", csv_path, json_path)

    print(
        f"Итог: точек={len(points)}, снимков на диске={n_saved}, каталог={out_dir}",
        file=sys.stdout,
    )
    return 0


def main() -> None:
    """Точка входа для консольной команды ``sparrow-fetch`` и ``python -m sparrow_loader.cli``.

    Разбирает аргументы и передаёт управление :func:`run_from_args`.

    Raises:
        SystemExit: С ненулевым кодом при ошибках argparse (стандартное поведение).
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    raise SystemExit(run_from_args(args))


if __name__ == "__main__":
    main()
