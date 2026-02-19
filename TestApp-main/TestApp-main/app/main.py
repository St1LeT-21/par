import asyncio

import uvicorn
from fastapi import FastAPI

from config import get_settings
from api.test import router as test_router

settings = get_settings()
app = FastAPI()
app.include_router(router=test_router)


async def main():
    if settings.DEBUG:
        uvicorn.run(app="main:app", reload=True, proxy_headers=True, host="0.0.0.0", port=8000)
    else:
        uvicorn.run(app="main:app", proxy_headers=True, host="0.0.0.0", port=8000, workers=4)

if __name__ == "__main__":
    asyncio.run(main())