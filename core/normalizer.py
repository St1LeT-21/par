from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .models import NewsItem

logger = logging.getLogger(__name__)

HEADER_MAX_LEN = 512
TEXT_MAX_LEN = 50_000
HASHTAG_MAX = 20


def _strip_html(raw: str) -> str:
    """Best-effort HTML tag removal using regex (no external deps)."""
    if not raw:
        return ""
    return re.sub(r"<[^>]+>", " ", raw)


def normalize_header(title: str) -> str:
    title = html.unescape(title or "").strip()
    title = re.sub(r"\s+", " ", title)
    return title[:HEADER_MAX_LEN]


def normalize_text(raw: str) -> str:
    cleaned = _strip_html(raw or "")
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.strip()
    return cleaned[:TEXT_MAX_LEN]


def _parse_datetime(entry: Dict[str, Any]) -> datetime:
    """
    Convert various feedparser date hints to a timezone-aware UTC datetime.
    Falls back to current UTC when missing.
    """
    for key in ("published_parsed", "updated_parsed"):
        tm = entry.get(key)
        if tm:
            try:
                return datetime(*tm[:6], tzinfo=timezone.utc)
            except Exception:
                logger.debug("Failed to parse %s in entry: %s", key, entry, exc_info=True)

    # ISO-like strings
    for key in ("published", "pubDate", "updated"):
        val = entry.get(key)
        if isinstance(val, str):
            try:
                # datetime.fromisoformat does not handle RFC2822; feedparser already parsed
                parsed = datetime.fromisoformat(val)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except Exception:
                continue

    return datetime.now(tz=timezone.utc)


def _normalize_hashtags(entry: Dict[str, Any]) -> List[str]:
    tags: Iterable[Any] = entry.get("tags", []) or entry.get("category", []) or []
    normalized = []
    for tag in tags:
        if isinstance(tag, dict):
            term = tag.get("term") or tag.get("label") or ""
        else:
            term = str(tag)
        term = term.strip().lower()
        if term and term not in normalized:
            normalized.append(term)
        if len(normalized) >= HASHTAG_MAX:
            break
    return normalized


def _extract_text(entry: Dict[str, Any]) -> str:
    """
    Extract body text from various RSS/Atom fields.
    Tries the most complete content first, then falls back to shorter summaries.
    """

    def _from_content(val: Any) -> str:
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, dict) and first.get("value"):
                return str(first["value"])
        if isinstance(val, dict) and val.get("value"):
            return str(val.get("value", ""))
        if isinstance(val, str):
            return val
        return ""

    # priority chain
    candidates = [
        entry.get("content"),
        entry.get("content:encoded"),
        entry.get("summary_detail", {}).get("value") if isinstance(entry.get("summary_detail"), dict) else None,
        entry.get("summary"),
        entry.get("description"),
        entry.get("yandex_fulltext"),
        entry.get("fulltext"),
        entry.get("subtitle"),
        entry.get("body"),
    ]

    for cand in candidates:
        text = _from_content(cand)
        if text and text.strip():
            return text
    return ""


def normalize_entry(entry: Dict[str, Any], source_name: str) -> NewsItem:
    header_raw = entry.get("title", "")
    text_raw = _extract_text(entry)
    date_dt = _parse_datetime(entry)
    hashtags = _normalize_hashtags(entry)
    link = entry.get("link", "")

    header = normalize_header(header_raw)
    text = normalize_text(text_raw)

    return NewsItem(
        header=header,
        text=text,
        date=date_dt,
        hashtags=hashtags,
        source_name=source_name,
        url=link,
    )
