from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import NewsItem

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_FILE = DATA_DIR / "raw.jsonl"
PROCESSED_FILE = DATA_DIR / "processed.jsonl"

# Locks to prevent concurrent writes from overlapping
_raw_lock = asyncio.Lock()
_proc_lock = asyncio.Lock()


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


async def append_raw(source: str, entries: Iterable[dict]) -> None:
    """
    Append raw feed entries (sanitized) to raw.jsonl.
    """
    _ensure_data_dir()
    now = datetime.now(tz=timezone.utc).isoformat()
    lines = []
    for entry in entries:
        lines.append(
            json.dumps(
                {
                    "fetched_at": now,
                    "source": source,
                    "entry": _sanitize_entry(entry),
                },
                ensure_ascii=False,
            )
        )
    if not lines:
        return

    async with _raw_lock:
        RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
        with RAW_FILE.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


async def append_processed(item: NewsItem, status: str) -> None:
    """
    Append normalized item to processed.jsonl with status (stored/duplicate/error).
    """
    _ensure_data_dir()
    payload = {
        "recorded_at": datetime.now(tz=timezone.utc).isoformat(),
        "status": status,
        "item": {
            "header": item.header,
            "text": item.text,
            "date": item.date.isoformat(),
            "hashtags": item.hashtags,
            "source_name": item.source_name,
            "url": item.url,
        },
    }
    line = json.dumps(payload, ensure_ascii=False)
    async with _proc_lock:
        with PROCESSED_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _sanitize_entry(entry: dict) -> dict[str, Any]:
    """
    Reduce feedparser entry to JSON-serializable snapshot.
    """
    def _first_content(contents: Any) -> str:
        if isinstance(contents, list) and contents:
            first = contents[0]
            if isinstance(first, dict) and "value" in first:
                return str(first.get("value", ""))
        if isinstance(contents, dict) and "value" in contents:
            return str(contents.get("value", ""))
        return ""

    return {
        "title": entry.get("title"),
        "link": entry.get("link"),
        "published": entry.get("published"),
        "updated": entry.get("updated"),
        "summary": entry.get("summary") or entry.get("description"),
        "content": _first_content(entry.get("content")),
    }
