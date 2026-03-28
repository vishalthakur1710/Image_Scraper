from __future__ import annotations

import logging
import random
from urllib.parse import quote_plus

from ..config import Settings
from ..models import CandidateImage, InputJob


class BrowserExtractor:
    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def supports(self, job: InputJob) -> bool:
        return self.settings.enable_browser_fallback

    def extract(self, job: InputJob, limit: int) -> list[CandidateImage]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Browser fallback is enabled, but playwright is not installed. "
                "Run: poetry install --extras bing-fallback"
            ) from exc

        if job.job_type == "keyword":
            target_url = f"https://www.bing.com/images/search?q={quote_plus(job.value)}&form=HDRSC3"
        else:
            target_url = job.value

        candidates: list[CandidateImage] = []
        seen_urls: set[str] = set()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1200},
            )
            page = context.new_page()
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                for _ in range(8):
                    page.mouse.wheel(0, random.randint(1000, 2200))
                    page.wait_for_timeout(random.randint(1000, 2000))
                    for handle in page.locator("img").element_handles():
                        src = handle.get_attribute("src") or handle.get_attribute("data-src")
                        if not src or src in seen_urls:
                            continue
                        seen_urls.add(src)
                        candidates.append(
                            CandidateImage(
                                source_type="browser",
                                source_name="playwright",
                                job_id=job.job_id,
                                page_url=target_url,
                                image_url=src,
                                source_id=src,
                            )
                        )
                        if len(candidates) >= limit:
                            return candidates
            finally:
                context.close()
                browser.close()

        return candidates
