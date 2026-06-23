"""Authentication tests — register, login, me, protected endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_client(db_session):
    """Create a test client with auth routes."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from backend.api.auth import router as auth_router
    from backend.api.data import router as data_router
    from backend.api.experiments import router as experiment_router
    from backend.core.dependencies import get_db

    app = FastAPI(title="Auth Test")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(data_router, prefix="/api/data")
    app.include_router(experiment_router, prefix="/api/experiments")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/register", json={
        "username": "alice", "email": "alice@test.com", "password": "secret123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@test.com"
    assert data["role"] == "user"
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client: AsyncClient):
    await auth_client.post("/api/auth/register", json={
        "username": "bob", "email": "bob@test.com", "password": "secret123",
    })
    resp = await auth_client.post("/api/auth/register", json={
        "username": "bob2", "email": "bob@test.com", "password": "secret456",
    })
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/register", json={
        "username": "eve", "email": "eve@test.com", "password": "12",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login(auth_client: AsyncClient):
    # Register first
    await auth_client.post("/api/auth/register", json={
        "username": "charlie", "email": "charlie@test.com", "password": "mypassword",
    })
    # Login
    resp = await auth_client.post("/api/auth/login", json={
        "email": "charlie@test.com", "password": "mypassword",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "charlie"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client: AsyncClient):
    await auth_client.post("/api/auth/register", json={
        "username": "dave", "email": "dave@test.com", "password": "correct",
    })
    resp = await auth_client.post("/api/auth/login", json={
        "email": "dave@test.com", "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(auth_client: AsyncClient):
    # Register and get token
    resp = await auth_client.post("/api/auth/register", json={
        "username": "frank", "email": "frank@test.com", "password": "test1234",
    })
    token = resp.json()["access_token"]

    # Call /me with token
    resp = await auth_client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "frank"
    assert data["email"] == "frank@test.com"


@pytest.mark.asyncio
async def test_me_without_token(auth_client: AsyncClient):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code in (401, 403)  # missing auth header


@pytest.mark.asyncio
async def test_list_users(auth_client: AsyncClient):
    # Register two users, get token, list
    resp = await auth_client.post("/api/auth/register", json={
        "username": "grace", "email": "grace@test.com", "password": "test1234",
    })
    token = resp.json()["access_token"]

    resp = await auth_client.get("/api/auth/users", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    assert any(u["username"] == "grace" for u in users)
