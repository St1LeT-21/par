from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List


@dataclass
class SourceConfig:
    name: str
    rss_url: str
    enabled: bool = True


@dataclass
class NewsItem:
    header: str
    text: str
    date: datetime
    hashtags: List[str]
    source_name: str
    url: str

    def __post_init__(self) -> None:
        # Ensure date is timezone-aware UTC to keep sorting consistent.
        if self.date.tzinfo is None:
            self.date = self.date.replace(tzinfo=timezone.utc)
        else:
            self.date = self.date.astimezone(timezone.utc)
