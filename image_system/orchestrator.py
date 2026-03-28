from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import Settings
from .downloader import ImageDownloader
from .extractors.api_extractor import ApiExtractor
from .extractors.browser_extractor import BrowserExtractor
from .extractors.html_extractor import HtmlExtractor
from .models import CandidateImage, InputJob
from .rate_limit import DomainRateLimiter
from .storage import MetadataStore


class PipelineOrchestrator:
    def __init__(self, settings: Settings, store: MetadataStore, logger: logging.Logger) -> None:
        self.settings = settings
        self.store = store
        self.logger = logger
        self.rate_limiter = DomainRateLimiter(settings.per_domain_delay_seconds)
        self.downloader = ImageDownloader(settings, store, self.rate_limiter, logger)
        self.extractors = [
            ApiExtractor(settings, logger),
            HtmlExtractor(settings, logger),
            BrowserExtractor(settings, logger),
        ]

    def run(self, jobs: list[InputJob]) -> int:
        candidates = self._discover_candidates(jobs)
        if not candidates:
            self.logger.warning("no_candidates_discovered")
            return 0

        downloaded = 0
        with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
            futures = {
                executor.submit(self.downloader.process_candidate, candidate): candidate
                for candidate in candidates
            }
            for future in as_completed(futures):
                status, detail = future.result()
                candidate = futures[future]
                self.logger.info(
                    "candidate_processed status=%s source=%s image_url=%s detail=%s",
                    status,
                    candidate.source_name,
                    candidate.image_url,
                    detail,
                )
                if status == "downloaded":
                    downloaded += 1
                if self.store.downloaded_count() >= self.settings.target_count:
                    self.logger.info("target_reached count=%s", self.store.downloaded_count())
                    break

        return downloaded

    def _discover_candidates(self, jobs: list[InputJob]) -> list[CandidateImage]:
        candidates: list[CandidateImage] = []
        discovery_limit = max(self.settings.target_count * 4, 200)

        for job in jobs:
            self.logger.info("discover_start job_id=%s job_type=%s value=%s", job.job_id, job.job_type, job.value)
            for extractor in self.extractors:
                if not extractor.supports(job):
                    continue
                try:
                    extracted = extractor.extract(job, discovery_limit)
                except Exception as exc:
                    self.logger.warning(
                        "discovery_failed extractor=%s job_id=%s reason=%s",
                        extractor.__class__.__name__,
                        job.job_id,
                        str(exc),
                    )
                    continue

                queued = 0
                for candidate in extracted:
                    if self.store.record_candidate(candidate):
                        candidates.append(candidate)
                        queued += 1
                self.logger.info(
                    "discover_complete extractor=%s job_id=%s extracted=%s queued=%s",
                    extractor.__class__.__name__,
                    job.job_id,
                    len(extracted),
                    queued,
                )

                if queued > 0 and extractor.__class__.__name__ == "ApiExtractor":
                    break

        return candidates
