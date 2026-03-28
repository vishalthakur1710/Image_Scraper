from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


JobType = Literal["keyword", "url"]
SourceType = Literal["api", "html", "browser"]


@dataclass(frozen=True)
class InputJob:
    job_id: str
    job_type: JobType
    value: str


@dataclass(frozen=True)
class CandidateImage:
    source_type: SourceType
    source_name: str
    job_id: str
    page_url: str
    image_url: str
    source_id: str


@dataclass(frozen=True)
class ValidatedImage:
    extension: str
    width: int
    height: int
    size_bytes: int
    content_hash: str


@dataclass(frozen=True)
class DownloadResult:
    candidate: CandidateImage
    file_path: Optional[Path]
    status: str
    message: str
