"""Auth API — register, login, and user management."""

from __future__ import annotations

from typing import Any

import httpx


class AuthAPI:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def register(
        self, username: str, email: str, password: str
    ) -> dict[str, Any]:
        resp = await self._client.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    async def login(self, email: str, password: str) -> dict[str, Any]:
        resp = await self._client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        resp.raise_for_status()
        return resp.json()

    async def me(self) -> dict[str, Any]:
        resp = await self._client.get("/api/auth/me")
        resp.raise_for_status()
        return resp.json()

    async def list_users(self, offset: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        resp = await self._client.get(
            "/api/auth/users", params={"offset": offset, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()
