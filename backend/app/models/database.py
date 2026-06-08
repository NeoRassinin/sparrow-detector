import aiosqlite
import json
from datetime import datetime
from typing import Optional, List
from ..config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                original_path TEXT NOT NULL,
                annotated_path TEXT NOT NULL,
                sparrow_count INTEGER NOT NULL,
                detections_json TEXT NOT NULL,
                processing_time_ms REAL,
                image_width INTEGER,
                image_height INTEGER
            )
        """)
        await db.commit()


async def insert_detection(
    filename: str,
    original_path: str,
    annotated_path: str,
    sparrow_count: int,
    detections: list,
    processing_time_ms: float,
    image_width: int,
    image_height: int,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO detections
            (filename, original_path, annotated_path, sparrow_count, detections_json, processing_time_ms, image_width, image_height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                original_path,
                annotated_path,
                sparrow_count,
                json.dumps(detections),
                processing_time_ms,
                image_width,
                image_height,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_detections(
    limit: int = 50, offset: int = 0, min_count: Optional[int] = None
) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM detections WHERE 1=1"
        params = []
        if min_count:
            query += " AND sparrow_count >= ?"
            params.append(min_count)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_detection_by_id(detection_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM detections WHERE id = ?", (detection_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def delete_detection(detection_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
        await db.commit()
        return True


async def get_total_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) as count FROM detections") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT
                COUNT(*) as total_detections,
                SUM(sparrow_count) as total_sparrows,
                AVG(sparrow_count) as avg_per_image,
                AVG(processing_time_ms) as avg_processing_time
            FROM detections
            """
        ) as cursor:
            row = await cursor.fetchone()
            if row[0] == 0:
                return {
                    "total_detections": 0,
                    "total_sparrows": 0,
                    "avg_per_image": 0,
                    "avg_confidence": 0,
                    "avg_processing_time": 0,
                }
            return {
                "total_detections": int(row[0]) or 0,
                "total_sparrows": int(row[1]) or 0,
                "avg_per_image": float(row[2]) or 0,
                "avg_processing_time": float(row[3]) or 0,
            }


async def get_timeseries_stats(
    period: str = "day",
) -> List[dict]:
    period_format = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m",
    }.get(period, "%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT
                strftime('{period_format}', timestamp) as period,
                COUNT(*) as detections,
                SUM(sparrow_count) as sparrows
            FROM detections
            GROUP BY period
            ORDER BY period ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
