"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "noone@example.com", "password": "testpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user, auth_headers):
    """Test getting current user info."""
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without auth."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_user, auth_headers):
    """Test changing password."""
    response = await client.post(
        "/api/auth/change-password",
        params={"current_password": "testpassword", "new_password": "newpassword"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify can login with new password
    response = await client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "newpassword"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, test_user, auth_headers):
    """Test changing password with wrong current password."""
    response = await client.post(
        "/api/auth/change-password",
        params={"current_password": "wrongpassword", "new_password": "newpassword"},
        headers=auth_headers,
    )
    assert response.status_code == 400
