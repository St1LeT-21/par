from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class NewsInputModel(BaseModel):
    title: str = Field(description="Tiltle of news")
    body: str = Field(description="Main text of news")
    source: Optional[str] = Field(description="Source of news")
    hash_tags: List[str] = Field(description="Hashtags of news", default_factory=list)
    published_at: Optional[datetime] = Field(description="Date and time of news", default_factory=datetime.utcnow)


class NewsInsertResultModel(BaseModel):
    news_id: int = Field(description="News ID")
    cluster_id: int = Field(description="Cluster ID")
    created: bool = Field(description="Created", default=False)