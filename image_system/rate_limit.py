from __future__ import annotations

import threading
import time
from collections import defaultdict
from urllib.parse import urlparse


class DomainRateLimiter:
    def __init__(self, min_delay_seconds: float) -> None:
        self.min_delay_seconds = min_delay_seconds
        self._lock = threading.Lock()
        self._last_seen: dict[str, float] = defaultdict(float)

    def wait(self, url: str) -> None:
        domain = urlparse(url).netloc.lower()
        if not domain or self.min_delay_seconds <= 0:
            return

        with self._lock:
            now = time.monotonic()
            last_seen = self._last_seen[domain]
            remaining = self.min_delay_seconds - (now - last_seen)
            if remaining > 0:
                time.sleep(remaining)
            self._last_seen[domain] = time.monotonic()
