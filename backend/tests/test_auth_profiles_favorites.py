import os
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("RATE_LIMIT_LOGIN_ATTEMPTS", "100")

from app.main import app


@pytest.mark.asyncio
async def test_auth_register_login_me_refresh_logout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # register
        email = f"t1+{uuid.uuid4().hex[:8]}@example.com"
        r = await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        assert r.status_code == 200

        # login
        r = await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        assert r.status_code == 200
        tok = r.json()["access_token"]

        # me
        r = await ac.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        assert r.json()["email"] == email

        # refresh (cookie set during login via Set-Cookie)
        # httpx AsyncClient persists cookies automatically
        r = await ac.post("/auth/refresh")
        assert r.status_code == 200
        new_tok = r.json()["access_token"]
        assert new_tok and isinstance(new_tok, str)

        # logout
        r = await ac.post("/auth/logout")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_profiles_and_favorites():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # register + login
        email = f"t2+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        r = await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        tok = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {tok}"}

        # profile get default
        r = await ac.get("/users/me/profile", headers=auth)
        assert r.status_code == 200
        prof = r.json()
        assert prof["preferred_metric"] == "XC0"

        # profile update
        r = await ac.patch("/users/me/profile", headers=auth, json={"display_name": "Pilot", "preferred_metric": "XC50"})
        assert r.status_code == 200
        prof = r.json()
        assert prof["display_name"] == "Pilot"
        assert prof["preferred_metric"] == "XC50"

        # favorites empty
        r = await ac.get("/users/me/favorites", headers=auth)
        assert r.status_code == 200
        assert r.json() == []

        # add favorite (assumes site_id 1 exists in dev DB; if not, just ensure endpoint works)
        await ac.post("/users/me/favorites", headers=auth, json={"site_id": 1})
        r = await ac.get("/users/me/favorites", headers=auth)
        assert r.status_code == 200
        assert 1 in r.json()

        # remove favorite
        await ac.delete("/users/me/favorites/1", headers=auth)
        r = await ac.get("/users/me/favorites", headers=auth)
        assert r.status_code == 200
        assert 1 not in r.json()


