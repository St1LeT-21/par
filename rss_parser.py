from __future__ import annotations

import asyncio
import logging
from typing import List

import feedparser
import httpx

from core.models import SourceConfig, NewsItem
from core.normalizer import normalize_entry

logger = logging.getLogger(__name__)

MAX_RSS_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
REQUEST_TIMEOUT = 10  # seconds
RETRY_ATTEMPTS = 3
BACKOFF_BASE = 2


async def fetch_and_parse(source: SourceConfig) -> List[NewsItem]:
    raw_data = await _download_feed(source)
    feed = feedparser.parse(raw_data)
    if feed.bozo:
        logger.warning("Feed parse warning for %s: %s", source.name, feed.bozo_exception)
    entries = feed.entries or []
    items = [normalize_entry(entry, source.name) for entry in entries]
    return items


async def _download_feed(source: SourceConfig) -> bytes:
    if not source.rss_url:
        raise ValueError(f"Source {source.name} missing rss_url")
    attempt = 0
    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        while attempt < RETRY_ATTEMPTS:
            attempt += 1
            try:
                resp = await client.get(source.rss_url, follow_redirects=True)
                resp.raise_for_status()
                data = bytearray()
                async for chunk in resp.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_RSS_SIZE_BYTES:
                        raise ValueError("Feed exceeds size limit while streaming")
                return bytes(data)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                delay = (BACKOFF_BASE ** (attempt - 1))
                logger.warning(
                    "Attempt %d/%d failed for %s: %s (sleep %ss)",
                    attempt,
                    RETRY_ATTEMPTS,
                    source.rss_url,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    assert last_err is not None
    raise last_err
