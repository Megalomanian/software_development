from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.auth import router as auth_router
from backend.api.data import router as data_router
from backend.api.deployments import router as deployment_router
from backend.api.experiments import router as experiment_router
from backend.api.models import router as model_router
from backend.api.monitoring import router as monitoring_router
from backend.core.auth import create_access_token, hash_password
from backend.core.dependencies import get_db
from backend.models_db.base import Base

# Ensure all ORM models are registered before create_all
from backend.models_db.user import User  # noqa: F401


def _create_test_app() -> FastAPI:
    """Create a FastAPI app without Prometheus instrumentator for testing."""
    app = FastAPI(title="ML Platform Test")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(data_router, prefix="/api/data", tags=["data"])
    app.include_router(experiment_router, prefix="/api/experiments", tags=["experiments"])
    app.include_router(model_router, prefix="/api/models", tags=["models"])
    app.include_router(deployment_router, prefix="/api/deployments", tags=["deployments"])
    app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture(scope="session")
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture(scope="session")
async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_test_user(db: AsyncSession) -> tuple[User, str]:
    """Create a test user and return (user, token)."""
    from backend.models_db.user import User as U

    user = U(
        username="testrunner",
        email="testrunner@test.com",
        hashed_password=hash_password("testsecret"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token({"sub": str(user.id)})
    return user, token


@pytest.fixture
async def db_session(engine, init_db) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Clean all tables before each test
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with auth token pre-configured.

    A test user is created automatically and the JWT token is
    included in all requests via default headers.
    """
    app = _create_test_app()

    # Create test user and generate token
    _, token = await _create_test_user(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    """Return auth headers for a fresh test user (for tests needing a specific user)."""
    _, token = await _create_test_user(db_session)
    return {"Authorization": f"Bearer {token}"}
