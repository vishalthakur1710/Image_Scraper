from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .models import CandidateImage, ValidatedImage


class MetadataStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = threading.Lock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    page_url TEXT NOT NULL,
                    image_url TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    content_hash TEXT UNIQUE,
                    file_path TEXT,
                    width INTEGER,
                    height INTEGER,
                    size_bytes INTEGER,
                    status TEXT NOT NULL,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_images_job_id ON images(job_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_images_status ON images(status)")

    def record_candidate(self, candidate: CandidateImage) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO images (
                    job_id, source_type, source_name, page_url, image_url, source_id, status, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.job_id,
                    candidate.source_type,
                    candidate.source_name,
                    candidate.page_url,
                    candidate.image_url,
                    candidate.source_id,
                    "queued",
                    "",
                ),
            )
            return cursor.rowcount > 0

    def mark_downloaded(self, candidate: CandidateImage, file_path: Path, validated: ValidatedImage) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE images
                SET content_hash = ?, file_path = ?, width = ?, height = ?, size_bytes = ?, status = ?, message = ?
                WHERE image_url = ?
                """,
                (
                    validated.content_hash,
                    str(file_path),
                    validated.width,
                    validated.height,
                    validated.size_bytes,
                    "downloaded",
                    "ok",
                    candidate.image_url,
                ),
            )

    def mark_failed(self, candidate: CandidateImage, status: str, message: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE images SET status = ?, message = ? WHERE image_url = ?",
                (status, message[:500], candidate.image_url),
            )

    def content_hash_exists(self, content_hash: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM images WHERE content_hash = ? LIMIT 1",
                (content_hash,),
            ).fetchone()
            return row is not None

    def downloaded_count(self) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM images WHERE status = 'downloaded'"
            ).fetchone()
            return int(row["count"])
