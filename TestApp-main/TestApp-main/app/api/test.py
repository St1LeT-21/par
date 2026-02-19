import random

from fastapi import APIRouter

from api.models import NewsInputModel, NewsInsertResultModel

router = APIRouter(prefix="/test", tags=["test-news"])

@router.post(path="/save_news", name="test:save_news", description="Test POST request", response_model=NewsInsertResultModel)
async def randomizer(news: NewsInputModel):
    return NewsInsertResultModel(
        news_id=random.randint(1, 100),
        cluster_id=random.randint(1, 100),
        created=random.random() < 0.7
    )