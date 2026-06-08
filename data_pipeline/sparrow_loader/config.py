"""Константы и настройки по умолчанию для обхода API и сохранения результатов."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: Базовый URL REST API, который использует карта (см. вкладка Network в браузере).
API_OBJECTS_URL: str = "https://sparrow.over.ru/api/objects"

#: Идентификаторы «сезонов» (акций переписи) в том виде, в каком их передаёт фронтенд
#: в параметре ``seasons``. Список нужно при необходимости дополнить, сверившись с Network.
DEFAULT_SEASON_IDS: tuple[int, ...] = (40, 20561, 27123, 45685, 61332)

#: Грубый охват территории РФ в градусах (широта/долгота WGS84).
#: Используется как стартовый прямоугольник, если пользователь не задал свой ``--bbox``.
RUSSIA_BBOX: tuple[float, float, float, float] = (
    41.0,
    82.0,
    18.5,
    169.0,
)

#: Заголовок User-Agent: некоторые CDN отвечают иначе на запросы без «браузерного» агента.
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (compatible; SparrowLoader/0.1; +https://vorobey.nbud.ru/)"
)


@dataclass(frozen=True, slots=True)
class HarvestSettings:
    """Снимок параметров одного «прогона» сбора данных.

    Attributes:
        api_url: Полный URL эндпоинта ``/api/objects``.
        season_ids: Набор идентификаторов акций (сезонов), которые нужно включить в запрос.
        bbox: Границы области обхода ``(min_lat, max_lat, min_lon, max_lon)``.
        initial_zoom: Начальный уровень ``zoom``, передаваемый в API (карта меняет его при
            приближении; при дроблении ячейки мы увеличиваем zoom).
        max_zoom: Верхняя граница zoom при рекурсивном дроблении (защита от бесконечного углубления).
        max_depth: Максимальная глубина рекурсивного деления прямоугольника на четыре части.
        min_bbox_size_deg: Минимальный размер стороны ячейки в градусах; ниже — остановка с предупреждением.
        request_delay_sec: Пауза между HTTP-запросами к API (снижает риск лимитов).
        region: Необязательное имя субъекта РФ в точности как в интерфейсе карты (фильтр ``region``).
        output_dir: Корневая папка для ``metadata.csv``, ``metadata.json`` и подкаталога ``images/``.
        images_subdir: Имя подкаталога внутри ``output_dir`` для файлов снимков.
        max_image_workers: Число параллельных загрузок изображений (не API).
        connect_timeout_sec: Таймаут установки соединения для ``requests``.
        read_timeout_sec: Таймаут чтения ответа для ``requests``.
        max_retries: Сколько раз повторить запрос при временных сбоях (5xx, сетевые ошибки).
        max_points: Если задано — остановить сбор после накопления стольки уникальных точек
            (для тестовых прогонов; кластеры в нераскрытых ячейках могут остаться).
        max_downloads: Если задано — скачать не более стольки файлов с непустым ``image_url``
            (остальные метаданные остаются в CSV/JSON без ``image_path``).
        image_read_timeout_sec: Таймаут чтения тела ответа при загрузке снимка (часто больше, чем у API).
    """

    api_url: str = API_OBJECTS_URL
    season_ids: tuple[int, ...] = DEFAULT_SEASON_IDS
    bbox: tuple[float, float, float, float] = RUSSIA_BBOX
    initial_zoom: int = 6
    max_zoom: int = 18
    max_depth: int = 18  # -> 22 -> 26 -> ...
    min_bbox_size_deg: float = 0.002  # -> 0.001 -> ...
    request_delay_sec: float = 0.25
    region: str | None = None
    output_dir: Path = field(default_factory=lambda: Path("sparrow_out"))
    images_subdir: str = "images"
    max_image_workers: int = 2
    connect_timeout_sec: float = 15.0
    read_timeout_sec: float = 60.0
    max_retries: int = 3
    max_points: int | None = None
    max_downloads: int | None = None
    image_read_timeout_sec: float = 120.0
