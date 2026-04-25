"""
PathForge API — Auth Integration Tests
=========================================
End-to-end integration tests for the full authentication lifecycle:
register → login → access protected endpoint → refresh → logout.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User

# ── Full Auth Lifecycle ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_lifecycle(client: AsyncClient) -> None:
    """Complete auth flow: register → login → protected → refresh → logout."""
    # 1. Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "lifecycle@pathforge.eu",
            "password": "Lifecycle123!",
            "full_name": "Lifecycle User",
        },
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["email"] == "lifecycle@pathforge.eu"

    # 2. Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "lifecycle@pathforge.eu",
            "password": "Lifecycle123!",
        },
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    # 3. Access protected endpoint with valid token
    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "lifecycle@pathforge.eu"

    # 4. Refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # 5. Access protected endpoint with refreshed token
    new_access_token = new_tokens["access_token"]
    me_response_2 = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert me_response_2.status_code == 200

    # Note: Logout is not tested here because it requires Redis for token
    # blacklisting. The full logout + revocation flow should be verified
    # in E2E tests with infrastructure (Redis) available.


# ── Direct DB Fixtures ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_client_accesses_protected_endpoint(
    auth_client: AsyncClient,
) -> None:
    """auth_client fixture provides pre-authenticated access to protected endpoints."""
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "integration@pathforge.eu"
    assert data["full_name"] == "Integration User"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_authenticated_user_fixture_creates_user(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """authenticated_user fixture creates a valid, active user in the database."""
    assert authenticated_user.id is not None
    assert authenticated_user.email == "integration@pathforge.eu"
    assert authenticated_user.is_active is True


# ── Auth Edge Cases ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    """Protected endpoints return 401 without authorization header."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(
    client: AsyncClient,
) -> None:
    """Protected endpoints return 401 with invalid token."""
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
