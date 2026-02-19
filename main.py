from __future__ import annotations

import asyncio
import logging
import time
from typing import List

from news_collector_git.backend_client import BackendClient
from news_collector_git.config_loader import load_sources
from news_collector_git.core.models import SourceConfig, NewsItem
from news_collector_git.rss_parser import fetch_and_parse

SLEEP_SECONDS = 300  # strictly per spec


async def process_source(source: SourceConfig, client: BackendClient) -> None:
    items = await fetch_and_parse(source)
    # newest to oldest
    items_sorted = sorted(items, key=lambda i: i.date, reverse=True)

    for item in items_sorted:
        payload = {
            "title": item.header,
            "body": item.text,
            "source": item.source_name,
            "hash_tags": item.hashtags,
            "published_at": item.date.isoformat(),
        }
        resp = await client.save_news(payload)
        created = bool(resp.get("created", False))
        if not created:
            # stop processing this feed immediately
            break


async def main() -> None:
    setup_logging()
    client = BackendClient()
    try:
        while True:
            sources: List[SourceConfig] = load_sources()
            for source in sources:
                await process_source(source, client)
            await asyncio.sleep(SLEEP_SECONDS)
    finally:
        await client.close()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    asyncio.run(main())
