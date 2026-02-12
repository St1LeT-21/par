from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
for p in (PARENT, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from news_collector_git.core import client_backend
from news_collector_git.core.file_sink import PROCESSED_FILE, RAW_FILE
from news_collector_git.core.scheduler import load_sources, process_source


TARGET_STORED = 10


def reset_files() -> None:
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)
    RAW_FILE.write_text("", encoding="utf-8")
    PROCESSED_FILE.write_text("", encoding="utf-8")


def count_stored() -> int:
    if not PROCESSED_FILE.exists():
        return 0
    cnt = 0
    with PROCESSED_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if '"status": "stored"' in line:
                cnt += 1
    return cnt


async def main() -> None:
    reset_files()
    # reset in-memory dedup state
    client_backend._seen.clear()  # type: ignore[attr-defined]

    sources, _ = load_sources()
    stored = 0
    iteration = 0

    while stored < TARGET_STORED:
        iteration += 1
        await asyncio.gather(*(process_source(s) for s in sources if s.enabled))
        stored = count_stored()
        print(f"Iteration {iteration}: stored={stored}")

    print(f"Reached {stored} stored items. Done.")


if __name__ == "__main__":
    asyncio.run(main())
