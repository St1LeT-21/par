from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from core.models import NewsItem, SourceConfig
from core.normalizer import normalize_entry

logger = logging.getLogger(__name__)

GNEWS_URL = "https://gnews.io/api/v4/top-headlines"
BACKOFF_BASE = 2


async def fetch_and_parse_gnews(source: SourceConfig, request_timeout: int, max_retries: int) -> List[NewsItem]:
    articles = await _fetch_json(source, request_timeout, max_retries)
    entries = [_to_entry_dict(article, source) for article in articles]
    items = [normalize_entry(entry, source.name) for entry in entries]
    return items


def _build_params(source: SourceConfig) -> Dict[str, Any]:
    params = {
        "token": source.api_token or source.params.get("api_token"),
        "lang": source.params.get("lang", "en"),
        "max": source.params.get("max", 50),
    }
    if topic := source.params.get("topic"):
        params["topic"] = topic
    if query := source.params.get("q"):
        params["q"] = query
    return params


async def _fetch_json(source: SourceConfig, request_timeout: int, max_retries: int) -> List[Dict[str, Any]]:
    params = _build_params(source)
    if not params.get("token"):
        raise ValueError(f"GNews source {source.name} requires api_token")

    attempt = 0
    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=request_timeout) as client:
        while attempt < max_retries:
            attempt += 1
            try:
                resp = await client.get(GNEWS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("articles", [])
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                delay = BACKOFF_BASE ** (attempt - 1)
                logger.warning(
                    "GNews attempt %d/%d failed for %s: %s (sleep %ss)",
                    attempt,
                    max_retries,
                    source.name,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    assert last_err is not None
    raise last_err


def _to_entry_dict(article: Dict[str, Any], source: SourceConfig) -> Dict[str, Any]:
    published = article.get("publishedAt")
    # normalize ISO with Z
    if isinstance(published, str) and published.endswith("Z"):
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(timezone.utc)
            published = dt.isoformat()
        except Exception:
            pass

    entry: Dict[str, Any] = {
        "title": article.get("title"),
        "summary": article.get("description"),
        "description": article.get("description"),
        "content": [{"value": article.get("content", "")}],
        "published": published,
        "link": article.get("url"),
        "tags": [],
    }
    if topic := source.params.get("topic"):
        entry["tags"].append(topic)
    if src := (article.get("source") or {}).get("name"):
        entry["tags"].append(src)
    return entry
