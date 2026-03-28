from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .models import InputJob


BLOCKED_DOMAINS = {
    "pinterest.com",
    "www.pinterest.com",
    "in.pinterest.com",
    "google.com",
    "www.google.com",
    "images.google.com",
}


@dataclass(frozen=True)
class Settings:
    output_dir: Path
    database_path: Path
    log_path: Path
    target_count: int
    min_width: int
    min_height: int
    min_size_bytes: int
    max_retries: int
    max_workers: int
    request_timeout: int
    per_domain_delay_seconds: float
    enable_html_fallback: bool
    enable_browser_fallback: bool
    pexels_api_key: str | None
    unsplash_access_key: str | None


def load_settings() -> Settings:
    load_dotenv()

    output_dir = Path(require_env("IMAGE_OUTPUT_DIR")).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    database_path = Path(os.getenv("IMAGE_DB_PATH", str(output_dir / "image_pipeline.sqlite3"))).expanduser()
    log_path = Path(os.getenv("IMAGE_LOG_PATH", str(output_dir / "pipeline.log"))).expanduser()

    return Settings(
        output_dir=output_dir,
        database_path=database_path,
        log_path=log_path,
        target_count=get_int_env("TARGET_IMAGE_COUNT", 100, minimum=1),
        min_width=get_int_env("MIN_WIDTH", 800, minimum=1),
        min_height=get_int_env("MIN_HEIGHT", 800, minimum=1),
        min_size_bytes=get_int_env("MIN_SIZE_BYTES", 100 * 1024, minimum=1),
        max_retries=get_int_env("MAX_RETRIES", 3, minimum=1),
        max_workers=get_int_env("MAX_DOWNLOAD_WORKERS", 4, minimum=1),
        request_timeout=get_int_env("REQUEST_TIMEOUT_SECONDS", 20, minimum=1),
        per_domain_delay_seconds=get_float_env("PER_DOMAIN_DELAY_SECONDS", 1.5, minimum=0.0),
        enable_html_fallback=get_bool_env("ENABLE_HTML_FALLBACK", True),
        enable_browser_fallback=get_bool_env("ENABLE_BROWSER_FALLBACK", False),
        pexels_api_key=os.getenv("PEXELS_API_KEY") or None,
        unsplash_access_key=os.getenv("UNSPLASH_ACCESS_KEY") or None,
    )


def load_jobs() -> list[InputJob]:
    load_dotenv()

    jobs: list[InputJob] = []

    keywords = parse_csv_env("INPUT_KEYWORDS")
    urls = parse_csv_env("INPUT_URLS")

    for keyword in keywords:
        jobs.append(InputJob(job_id=make_job_id("kw", keyword), job_type="keyword", value=keyword))

    for url in urls:
        validate_input_url(url)
        jobs.append(InputJob(job_id=make_job_id("url", url), job_type="url", value=url))

    if not jobs:
        raise RuntimeError("Provide at least one INPUT_KEYWORDS or INPUT_URLS entry in .env.")

    return jobs


def parse_csv_env(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required in the .env file.")
    return value


def get_int_env(name: str, default: int, minimum: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer. Received: {raw_value}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}. Received: {value}")
    return value


def get_float_env(name: str, default: float, minimum: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number. Received: {raw_value}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}. Received: {value}")
    return value


def get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, "true" if default else "false").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_") or "item"


def make_job_id(prefix: str, value: str) -> str:
    return f"{prefix}_{slugify(value)[:80]}"


def validate_input_url(url: str) -> None:
    lower_url = url.lower()
    if any(domain in lower_url for domain in BLOCKED_DOMAINS):
        raise RuntimeError(
            f"Blocked source URL detected: {url}. Restricted sources like Pinterest and Google are not supported."
        )
