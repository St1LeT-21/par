from __future__ import annotations

import asyncio
import logging
import os
from typing import List

from backend_client import BackendClient
from config_loader import load_sources
from core.models import SourceConfig
from gnews_adapter import fetch_and_parse_gnews
from rss_parser import fetch_and_parse


def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except Exception:
        return default


def get_config():
    return {
        "sleep_seconds": env_int("SLEEP_SECONDS", 300),
        "request_timeout": env_int("REQUEST_TIMEOUT", 10),
        "max_retries": env_int("MAX_RETRIES", 3),
        "backend_base_url": os.getenv("BACKEND_BASE_URL", "http://localhost:8080"),
        "backend_endpoint": os.getenv("BACKEND_SAVE_NEWS_ENDPOINT", "/test/save_news"),
        "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
    }


async def process_source(source: SourceConfig, client: BackendClient, cfg: dict) -> None:
    logging.info("Processing source: %s", source.name)
    if source.type == "gnews":
        items = await fetch_and_parse_gnews(
            source, request_timeout=cfg["request_timeout"], max_retries=cfg["max_retries"]
        )
    else:
        items = await fetch_and_parse(
            source, request_timeout=cfg["request_timeout"], max_retries=cfg["max_retries"]
        )

    items_sorted = sorted(items, key=lambda i: i.date, reverse=True)

    for item in items_sorted:
        payload = {
            "title": item.header,
            "body": item.text,
            "source": item.source_name,
            "hash_tags": item.hashtags,
            "published_at": item.date.isoformat(),
        }
        try:
            resp = await client.save_news(payload)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Backend error for %s: %s. Treating as created=false", source.name, exc)
            logging.info("Backend returned created=false, stopping source %s", source.name)
            return

        created = bool(resp.get("created", False))
        logging.info("Sent news to backend (source=%s, created=%s)", source.name, created)
        if not created:
            logging.info("Backend returned created=false, stopping source %s", source.name)
            return

    logging.info("Finished source: %s", source.name)


async def main() -> None:
    cfg = get_config()
    setup_logging(cfg["log_level"])
    logging.info("Parser started")
    client = BackendClient(
        base_url=cfg["backend_base_url"],
        endpoint=cfg["backend_endpoint"],
        timeout=cfg["request_timeout"],
    )
    try:
        while True:
            logging.info("Starting new parsing iteration")
            sources: List[SourceConfig] = load_sources()
            for source in sources:
                try:
                    await process_source(source, client, cfg)
                except Exception as exc:  # noqa: BLE001
                    logging.warning("Source %s failed: %s", source.name, exc)
            logging.info("Sleeping for %s seconds", cfg["sleep_seconds"])
            await asyncio.sleep(cfg["sleep_seconds"])
    finally:
        await client.close()


def setup_logging(level: str) -> None:
    numeric = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    asyncio.run(main())
