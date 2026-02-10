from __future__ import annotations

import asyncio
import logging
import random
from typing import List

import feedparser

try:
    import httpx
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError("httpx is required for rss_adapter") from exc

from .models import NewsItem, SourceConfig
from .normalizer import normalize_entry

logger = logging.getLogger(__name__)

MAX_RSS_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
REQUEST_TIMEOUT = 10  # seconds
RETRY_ATTEMPTS = 3
BACKOFF_BASE = 2


class SourceAdapter:
    async def fetch(self) -> List[NewsItem]:  # pragma: no cover - interface
        raise NotImplementedError


class RssAdapter(SourceAdapter):
    def __init__(self, source: SourceConfig) -> None:
        self.source = source

    async def fetch(self) -> List[NewsItem]:
        raw_data = await self._download_feed()
        feed = feedparser.parse(raw_data)

        if feed.bozo:  # bozo flag means parse issues
            logger.warning("Feed parse warning for %s: %s", self.source.name, feed.bozo_exception)

        entries = feed.entries or []
        items = [normalize_entry(entry, self.source.name) for entry in entries]
        return items

    async def _download_feed(self) -> bytes:
        attempt = 0
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            while attempt < RETRY_ATTEMPTS:
                attempt += 1
                try:
                    resp = await client.get(self.source.rss_url, follow_redirects=True)
                    resp.raise_for_status()
                    content_length = resp.headers.get("content-length")
                    try:
                        if content_length and int(content_length) > MAX_RSS_SIZE_BYTES:
                            raise ValueError("Feed exceeds size limit")
                    except ValueError:
                        # If header is malformed, ignore and rely on streaming guard
                        logger.debug("Invalid content-length header on %s: %s", self.source.rss_url, content_length)

                    data = bytearray()
                    async for chunk in resp.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > MAX_RSS_SIZE_BYTES:
                            raise ValueError("Feed exceeds size limit while streaming")
                    return bytes(data)
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempt,
                        RETRY_ATTEMPTS,
                        self.source.rss_url,
                        exc,
                    )
                    # Exponential backoff with jitter: 1s, 2s, ...
                    delay = (BACKOFF_BASE ** (attempt - 1)) + random.random()
                    await asyncio.sleep(delay)

        assert last_err is not None
        logger.error("Failed to fetch %s after %d attempts", self.source.rss_url, RETRY_ATTEMPTS)
        raise last_err
