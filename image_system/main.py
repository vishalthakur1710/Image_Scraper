from __future__ import annotations

import sys

from .config import load_jobs, load_settings
from .logging_utils import configure_logging
from .orchestrator import PipelineOrchestrator
from .storage import MetadataStore


def main() -> int:
    try:
        settings = load_settings()
        jobs = load_jobs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    logger = configure_logging(settings.log_path)
    store = MetadataStore(settings.database_path)
    orchestrator = PipelineOrchestrator(settings, store, logger)
    downloaded = orchestrator.run(jobs)

    total = store.downloaded_count()
    print(f"New downloads this run: {downloaded}")
    print(f"Total downloaded images in database: {total}")
    print(f"Images directory: {settings.output_dir}")
    print(f"Metadata database: {settings.database_path}")
    print(f"Log file: {settings.log_path}")

    if total < settings.target_count:
        print(
            "Target not reached. Add more keywords, approved URLs, or enable browser fallback.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
