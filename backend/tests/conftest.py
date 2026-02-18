"""
Pytest configuration and fixtures for MyHours tests.
"""

import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.employee import Employee
from app.core.security import get_password_hash, create_access_token

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> Employee:
    """Create a test user."""
    from datetime import date

    user = Employee(
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User",
        hire_date=date(2024, 1, 1),
        pay_period_group="A",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_manager(db_session: AsyncSession) -> Employee:
    """Create a test manager user."""
    from datetime import date

    user = Employee(
        email="manager@example.com",
        password_hash=get_password_hash("testpassword"),
        first_name="Test",
        last_name="Manager",
        hire_date=date(2024, 1, 1),
        pay_period_group="A",
        is_manager=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: Employee) -> dict:
    """Generate auth headers for test user."""
    token = create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_auth_headers(test_manager: Employee) -> dict:
    """Generate auth headers for test manager."""
    token = create_access_token(
        data={"sub": str(test_manager.id), "email": test_manager.email}
    )
    return {"Authorization": f"Bearer {token}"}
