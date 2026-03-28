from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..config import Settings
from ..models import CandidateImage, InputJob


class HtmlExtractor:
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
        return self.settings.enable_html_fallback and job.job_type == "url"

    def extract(self, job: InputJob, limit: int) -> list[CandidateImage]:
        response = self.session.get(job.value, timeout=self.settings.request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        candidates: list[CandidateImage] = []
        seen_urls: set[str] = set()

        for image in soup.find_all("img"):
            raw_url = image.get("src") or image.get("data-src") or image.get("data-lazy-src")
            if not raw_url:
                continue
            image_url = urljoin(job.value, raw_url)
            if image_url in seen_urls:
                continue
            seen_urls.add(image_url)

            candidates.append(
                CandidateImage(
                    source_type="html",
                    source_name="html_page",
                    job_id=job.job_id,
                    page_url=job.value,
                    image_url=image_url,
                    source_id=image_url,
                )
            )
            if len(candidates) >= limit:
                break

        return candidates
