from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.models import SourceConfig

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "sources.yaml"


def load_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> List[SourceConfig]:
    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    sources_data = raw.get("sources", [])
    sources: List[SourceConfig] = []
    for item in sources_data:
        if not item.get("enabled", True):
            continue
        try:
            sources.append(
                SourceConfig(
                    name=item["name"],
                    rss_url=item.get("rss_url"),
                    type=item.get("type", "rss"),
                    params=item.get("params", {}),
                    api_token=item.get("api_token"),
                    enabled=True,
                )
            )
        except KeyError:
            continue
    return sources
