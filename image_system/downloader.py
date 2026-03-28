from __future__ import annotations

import logging
import random
import time
from pathlib import Path

import requests

from .config import Settings, slugify
from .models import CandidateImage
from .rate_limit import DomainRateLimiter
from .storage import MetadataStore
from .validator import validate_image_bytes


class ImageDownloader:
    def __init__(
        self,
        settings: Settings,
        store: MetadataStore,
        rate_limiter: DomainRateLimiter,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.store = store
        self.rate_limiter = rate_limiter
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )

    def process_candidate(self, candidate: CandidateImage) -> tuple[str, str]:
        try:
            image_bytes = self._download_bytes(candidate.image_url)
            validated = validate_image_bytes(image_bytes, self.settings)

            if self.store.content_hash_exists(validated.content_hash):
                self.store.mark_failed(candidate, "duplicate", "content hash already exists")
                return "duplicate", "content hash already exists"

            file_path = self._build_file_path(candidate, validated.extension, validated.content_hash)
            file_path.write_bytes(image_bytes)
            self.store.mark_downloaded(candidate, file_path, validated)
            return "downloaded", str(file_path)
        except Exception as exc:
            message = str(exc)
            self.store.mark_failed(candidate, "failed", message)
            self.logger.warning("download_failed image_url=%s reason=%s", candidate.image_url, message)
            return "failed", message

    def _download_bytes(self, url: str) -> bytes:
        last_error: Exception | None = None

        for attempt in range(1, self.settings.max_retries + 1):
            try:
                self.rate_limiter.wait(url)
                response = self.session.get(url, timeout=self.settings.request_timeout)
                response.raise_for_status()
                return response.content
            except requests.RequestException as exc:
                last_error = exc
                if attempt == self.settings.max_retries:
                    break
                sleep_seconds = min(10.0, (2 ** (attempt - 1)) + random.uniform(0.1, 0.9))
                time.sleep(sleep_seconds)

        raise RuntimeError(f"request failed after retries: {last_error}")

    def _build_file_path(self, candidate: CandidateImage, extension: str, content_hash: str) -> Path:
        prefix = slugify(candidate.job_id)
        return self.settings.output_dir / f"{prefix}_{content_hash}.{extension}"
