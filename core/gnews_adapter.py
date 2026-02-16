from __future__ import annotations

import logging
from typing import List, Dict, Any

import httpx

from .models import NewsItem, SourceConfig
from .normalizer import normalize_entry

logger = logging.getLogger(__name__)

GNEWS_URL = "https://gnews.io/api/v4/top-headlines"
REQUEST_TIMEOUT = 10  # seconds
RETRY_ATTEMPTS = 3


class GNewsAdapter:
    def __init__(self, source: SourceConfig) -> None:
        self.source = source
        if not source.api_token:
            raise ValueError(f"GNewsAdapter requires api_token for source {source.name}")

    async def fetch(self) -> List[NewsItem]:
        entries = await self._fetch_json()
        items = [normalize_entry(self._to_entry_dict(article), self.source.name) for article in entries]
        return items

    def _build_params(self) -> Dict[str, Any]:
        params = {
            "token": self.source.api_token,
            "lang": self.source.params.get("lang", "en"),
            "max": self.source.params.get("max", 50),
        }
        if topic := self.source.params.get("topic"):
            params["topic"] = topic
        if query := self.source.params.get("q"):
            params["q"] = query
        return params

    async def _fetch_json(self) -> List[Dict[str, Any]]:
        params = self._build_params()
        attempt = 0
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            while attempt < RETRY_ATTEMPTS:
                attempt += 1
                try:
                    resp = await client.get(GNEWS_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    articles = data.get("articles", [])
                    return articles
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "GNews attempt %d/%d failed for %s: %s",
                        attempt,
                        RETRY_ATTEMPTS,
                        self.source.name,
                        exc,
                    )
        assert last_err is not None
        raise last_err

    def _to_entry_dict(self, article: Dict[str, Any]) -> Dict[str, Any]:
        # Map GNews JSON fields to a feedparser-like dict for reuse of normalize_entry
        entry: Dict[str, Any] = {
            "title": article.get("title"),
            "summary": article.get("description"),
            "description": article.get("description"),
            "content": [{"value": article.get("content", "")}],
            "published": article.get("publishedAt"),
            "link": article.get("url"),
            "tags": [],
        }
        if topic := self.source.params.get("topic"):
            entry["tags"].append(topic)
        if src := article.get("source", {}).get("name"):
            entry["tags"].append(src)
        return entry
