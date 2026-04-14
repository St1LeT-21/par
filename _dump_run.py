"""
Local runner to inspect what payloads would be sent to the backend.
Writes a JSONL dump to ./data/dump.jsonl without hitting the backend.
"""

import asyncio
import json
from pathlib import Path

from config_loader import load_sources
from rss_parser import fetch_and_parse
from gnews_adapter import fetch_and_parse_gnews
from core.normalizer import normalize_text

DUMP_PATH = Path(__file__).resolve().parent / "data" / "dump.jsonl"
DUMP_PATH.parent.mkdir(exist_ok=True, parents=True)


async def collect():
    sources = load_sources()
    rows = []
    for src in sources:
        try:
            items = await (
                fetch_and_parse_gnews(src, request_timeout=10, max_retries=3)
                if src.type == "gnews"
                else fetch_and_parse(src, request_timeout=10, max_retries=3)
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[SKIP] {src.name}: {exc}")
            continue
        for it in items:
            rows.append(
                {
                    "source_name": src.name,
                    "type": src.type,
                    "title": it.header,
                    "body_len": len(it.text),
                    "body_sample": it.text[:300],
                    "url": it.url,
                    "hashtags": it.hashtags,
                    "published_at": it.date.isoformat(),
                }
            )
    with DUMP_PATH.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} items to {DUMP_PATH}")


if __name__ == "__main__":
    asyncio.run(collect())
