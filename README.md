#this is vishal workspace
# Production Image Download Pipeline

This project is a production-style starter for collecting high-quality images from approved sources with:

- API-first extraction
- HTML fallback for direct page URLs
- Optional Playwright browser fallback
- Validation for file size, format, and resolution
- SQLite metadata storage for deduplication and checkpointing
- Thread-pooled downloads with per-domain throttling

It intentionally does not support Pinterest or Google Images.

## Architecture

- `image_system/config.py`: environment-driven settings and job loading
- `image_system/extractors/api_extractor.py`: Pexels and Unsplash discovery
- `image_system/extractors/html_extractor.py`: static HTML image extraction from approved URLs
- `image_system/extractors/browser_extractor.py`: Playwright-based fallback
- `image_system/downloader.py`: retrying downloader with exponential backoff
- `image_system/validator.py`: image validation and hashing
- `image_system/storage.py`: SQLite metadata store
- `image_system/orchestrator.py`: end-to-end pipeline orchestration
- `image_system/main.py`: CLI entrypoint

## Setup

```bash
poetry install
cp .env.example .env
```

Optional browser fallback:

```bash
poetry install --extras bing-fallback
poetry run playwright install chromium
```

## Configure

Edit `.env`:

```env
PEXELS_API_KEY=your_pexels_key
UNSPLASH_ACCESS_KEY=
INPUT_KEYWORDS=thin lips,full face portrait
INPUT_URLS=
IMAGE_OUTPUT_DIR=/absolute/path/to/image_output
TARGET_IMAGE_COUNT=100
MIN_WIDTH=800
MIN_HEIGHT=800
MIN_SIZE_BYTES=102400
MAX_RETRIES=3
MAX_DOWNLOAD_WORKERS=4
REQUEST_TIMEOUT_SECONDS=20
PER_DOMAIN_DELAY_SECONDS=1.5
ENABLE_HTML_FALLBACK=true
ENABLE_BROWSER_FALLBACK=false
```

## Run

```bash
poetry run python -m image_system.main
```

## Output

- Images are saved into `IMAGE_OUTPUT_DIR`
- Metadata and dedupe state are stored in `image_pipeline.sqlite3`
- Logs are written to `pipeline.log`
