from __future__ import annotations

import logging

import requests

from ..config import Settings
from ..models import CandidateImage, InputJob


class ApiExtractor:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
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

    def supports(self, job: InputJob) -> bool:
        return job.job_type == "keyword" and bool(self.settings.pexels_api_key or self.settings.unsplash_access_key)

    def extract(self, job: InputJob, limit: int) -> list[CandidateImage]:
        candidates: list[CandidateImage] = []
        if self.settings.pexels_api_key:
            candidates.extend(self._fetch_pexels(job, limit))
        if len(candidates) < limit and self.settings.unsplash_access_key:
            candidates.extend(self._fetch_unsplash(job, limit - len(candidates)))
        return candidates[:limit]

    def _fetch_pexels(self, job: InputJob, limit: int) -> list[CandidateImage]:
        headers = {"Authorization": self.settings.pexels_api_key or ""}
        per_page = 80
        results: list[CandidateImage] = []

        for page in range(1, max(2, min(10, (limit + per_page - 1) // per_page + 1))):
            response = self.session.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params={"query": job.value, "per_page": per_page, "page": page},
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            for photo in response.json().get("photos", []):
                src = photo.get("src", {})
                image_url = src.get("original") or src.get("large2x") or src.get("large")
                if not image_url:
                    continue
                results.append(
                    CandidateImage(
                        source_type="api",
                        source_name="pexels",
                        job_id=job.job_id,
                        page_url=f"https://www.pexels.com/search/{job.value}/",
                        image_url=image_url,
                        source_id=str(photo.get("id", "")),
                    )
                )
                if len(results) >= limit:
                    return results
        return results

    def _fetch_unsplash(self, job: InputJob, limit: int) -> list[CandidateImage]:
        headers = {"Authorization": f"Client-ID {self.settings.unsplash_access_key}"}
        per_page = 30
        results: list[CandidateImage] = []

        for page in range(1, max(2, min(10, (limit + per_page - 1) // per_page + 1))):
            response = self.session.get(
                "https://api.unsplash.com/search/photos",
                headers=headers,
                params={"query": job.value, "per_page": per_page, "page": page},
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            for photo in response.json().get("results", []):
                urls = photo.get("urls", {})
                image_url = urls.get("raw") or urls.get("full") or urls.get("regular")
                if not image_url:
                    continue
                results.append(
                    CandidateImage(
                        source_type="api",
                        source_name="unsplash",
                        job_id=job.job_id,
                        page_url=photo.get("links", {}).get("html", ""),
                        image_url=image_url,
                        source_id=str(photo.get("id", "")),
                    )
                )
                if len(results) >= limit:
                    return results
        return results
