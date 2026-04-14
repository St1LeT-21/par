import asyncio
import json

from config_loader import load_sources
from rss_parser import fetch_and_parse
from gnews_adapter import fetch_and_parse_gnews


async def main():
    sources = load_sources()
    for src in sources[:3]:
        print(f"=== {src.name} ({src.type}) ===")
        try:
            if src.type == "gnews":
                items = await fetch_and_parse_gnews(src, request_timeout=10, max_retries=3)
            else:
                items = await fetch_and_parse(src, request_timeout=10, max_retries=3)
        except Exception as e:
            print("error:", e)
            continue
        for it in items[:3]:
            print(
                json.dumps(
                    {
                        "title": it.header,
                        "text_len": len(it.text),
                        "text_sample": it.text[:200],
                        "url": it.url,
                    },
                    ensure_ascii=False,
                )
            )
        print()


if __name__ == "__main__":
    asyncio.run(main())
