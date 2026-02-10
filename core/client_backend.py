"""
Backend API integration.

The spec mandates two functions:
    - check_if_news_exists
    - push_news_to_db

Replace the stub implementations with real backend calls (HTTP/DB/RPC).
The current in-memory fallback keeps the pipeline runnable for local tests.
"""

from __future__ import annotations

import logging
from typing import List, Set, Tuple

from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory fallback store keyed by (header, source_name)
_seen: Set[Tuple[str, str]] = set()


def check_if_news_exists(header: str, source_name: str) -> bool:
    """
    Check if the news item already exists in backend storage.
    Replace this stub with a real API call when integrating.
    """
    key = (header, source_name)
    exists = key in _seen
    logger.debug("check_if_news_exists: %s -> %s", key, exists)
    return exists


def push_news_to_db(
    header: str,
    text: str,
    date: datetime,
    hashtags: List[str],
    source_name: str,
    url: str,
) -> None:
    """
    Persist a news item to backend storage.
    Replace this stub with a real API call when integrating.
    """
    key = (header, source_name)
    _seen.add(key)
    logger.info("push_news_to_db: stored %s from %s", header, source_name)
    logger.debug(
        "payload: header=%s text_len=%d date=%s hashtags=%s url=%s",
        header,
        len(text),
        date.isoformat(),
        hashtags,
        url,
    )
