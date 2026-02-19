from __future__ import annotations

import os
from typing import Any, Dict

import httpx


class BackendClient:
    """
    HTTP client for the provided backend.
    """

    def __init__(self, base_url: str | None = None, timeout: int = 10) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_BASE_URL") or "http://localhost:8000").rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def save_news(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/test/save_news"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
