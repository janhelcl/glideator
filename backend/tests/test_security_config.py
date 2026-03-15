import pytest

from app import security


def test_normalize_email_trims_and_lowercases():
    assert security.normalize_email("  Test.User@Example.COM ") == "test.user@example.com"


def test_get_jwt_secret_allows_dev_fallback(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    assert security.get_jwt_secret() == "dev-insecure-secret-change-me"


def test_get_jwt_secret_requires_value_in_production(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be set in production"):
        security.get_jwt_secret()


def test_cookie_secure_defaults_to_true_in_production(monkeypatch):
    monkeypatch.delenv("JWT_COOKIE_SECURE", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    assert security.is_cookie_secure() is True


def test_cookie_secure_respects_explicit_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_COOKIE_SECURE", "false")

    assert security.is_cookie_secure() is False
