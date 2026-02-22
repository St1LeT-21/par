from __future__ import annotations

import asyncio
import logging
from typing import List

import feedparser
import httpx

from core.models import SourceConfig, NewsItem
from core.normalizer import normalize_entry, normalize_text

logger = logging.getLogger(__name__)

MAX_RSS_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BACKOFF_BASE = 2


async def fetch_and_parse(source: SourceConfig, request_timeout: int, max_retries: int) -> List[NewsItem]:
    raw_data = await _download_feed(source, request_timeout, max_retries)
    feed = feedparser.parse(raw_data)
    if feed.bozo:
        logger.warning("Feed parse warning for %s: %s", source.name, feed.bozo_exception)
    entries = feed.entries or []
    items = [normalize_entry(entry, source.name) for entry in entries]
    # fallback: fetch full article text if missing
    for item in items:
        if item.url and not item.text.strip():
            full = await _fetch_full_text(item.url, request_timeout)
            if full:
                item.text = normalize_text(full)
    return items


async def _download_feed(source: SourceConfig, request_timeout: int, max_retries: int) -> bytes:
    if not source.rss_url:
        raise ValueError(f"Source {source.name} missing rss_url")
    attempt = 0
    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=request_timeout) as client:
        while attempt < max_retries:
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
                    "RSS fetch failed for %s (attempt %d/%d): %s. Sleeping %ss",
                    source.name,
                    attempt,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    assert last_err is not None
    logger.warning("Source %s failed after %d attempts, skipping", source.name, max_retries)
    raise last_err


async def _fetch_full_text(url: str, timeout: int) -> str:
    """
    Best-effort fetch of article body when RSS entry has no text.
    """
    try:
        import bs4  # type: ignore
    except Exception:
        return ""

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to fetch full text %s: %s", url, exc)
        return ""

    try:
        soup = bs4.BeautifulSoup(html, "html.parser")
        # common containers
        selectors = [
            "article",
            "div.article__body",
            "div.article-body",
            "div#article",
            "div.content",
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        # fallback to all paragraphs
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
        return text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to parse full text %s: %s", url, exc)
        return ""
