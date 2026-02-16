from __future__ import annotations

import asyncio
import logging
import json
from pathlib import Path
from typing import List, Tuple

from .client_backend import check_if_news_exists, push_news_to_db
from .file_sink import append_processed, append_raw
from .models import NewsItem, SourceConfig
from .rss_adapter import RssAdapter
from .gnews_adapter import GNewsAdapter

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "sources.yaml"


def load_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> Tuple[List[SourceConfig], int]:
    """
    Read YAML configuration and return source configs + poll interval.
    """
    with config_path.open("r", encoding="utf-8") as f:
        raw = _load_config(f)

    poll_interval = int(raw.get("poll_interval_seconds", 300))
    sources_data = raw.get("sources", [])

    sources: List[SourceConfig] = []
    for item in sources_data:
        try:
            sources.append(
                SourceConfig(
                    name=item["name"],
                    rss_url=item.get("rss_url"),
                    type=item.get("type", "rss"),
                    params=item.get("params", {}),
                    api_token=item.get("api_token"),
                    enabled=bool(item.get("enabled", True)),
                )
            )
        except KeyError as exc:
            logger.warning("Skipping source missing key %s: %s", exc, item)
    return sources, poll_interval


def _load_config(handle) -> dict:
    """
    Load config as JSON. The config file is stored in JSON (which is also valid YAML).
    """
    return json.load(handle)


async def process_source(source: SourceConfig) -> None:
    adapter = _get_adapter(source)
    try:
        raw_entries, items = await adapter.fetch_with_raw()  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch %s: %s", source.name, exc)
        return

    # Save raw snapshot
    await append_raw(source.name, raw_entries)

    items_sorted = sorted(items, key=lambda i: i.date, reverse=True)
    for item in items_sorted:
        if check_if_news_exists(item.header, source.name):
            logger.debug("Existing item encountered for %s, stopping iteration", source.name)
            await append_processed(item, status="duplicate")
            break
        push_news_to_db(
            header=item.header,
            text=item.text,
            date=item.date,
            hashtags=item.hashtags,
            source_name=item.source_name,
            url=item.url,
        )
        await append_processed(item, status="stored")


async def run_forever(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """
    Main scheduler loop: fetches all enabled sources in parallel every poll interval.
    """
    sources, poll_interval = load_sources(config_path)
    logger.info("Loaded %d sources; poll interval=%ds", len(sources), poll_interval)

    while True:
        enabled_sources = [s for s in sources if s.enabled]
        logger.info("Starting poll for %d sources", len(enabled_sources))

        tasks = [asyncio.create_task(process_source(source)) for source in enabled_sources]
        if tasks:
            # gather with return_exceptions to keep loop alive on errors
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("Source task error: %s", res)

        await asyncio.sleep(poll_interval)


async def run_once(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """
    Run a single poll cycle; handy for tests or one-shot execution.
    """
    sources, _ = load_sources(config_path)
    tasks = [process_source(s) for s in sources if s.enabled]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _get_adapter(source: SourceConfig):
    if source.type == "gnews":
        class Wrapper(GNewsAdapter):
            async def fetch_with_raw(self):  # type: ignore[override]
                items = await self.fetch()
                return [], items

        return Wrapper(source)

    class WrapperRSS(RssAdapter):
        async def fetch_with_raw(self):  # type: ignore[override]
            return await super().fetch_with_raw()

    return WrapperRSS(source)
