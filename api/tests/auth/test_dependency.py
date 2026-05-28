"""Tests for require_user — happy path + every documented rejection path.

We exercise the dependency directly (not via the HTTP layer) so the failure
modes are unambiguous. Phase 5's `tests/test_runs_api.py` covers the HTTP
integration where the dependency is wired into routers.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import HttpUrl

from agentgenesis_api.auth.dependency import require_user
from agentgenesis_api.auth.models import STUB_USER
from agentgenesis_api.config import Settings


def _real_settings(**overrides) -> Settings:
    """Settings with use_stub_nodes=False so the real validation path runs."""
    base = dict(
        environment="dev",
        entra_tenant_id="test-tenant",
        entra_client_id="test-client-id",
        entra_client_secret="test-secret",
        anthropic_api_key="test",
        use_stub_nodes=False,
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ────────────────────────── stub mode short-circuit ──────────────────────────


async def test_stub_mode_returns_stub_user_without_token() -> None:
    settings = Settings(use_stub_nodes=True, environment="test", anthropic_api_key="x")  # type: ignore[call-arg]
    result = await require_user(authorization=None, settings=settings, jwks_client=None)  # type: ignore[arg-type]
    assert result is STUB_USER


# ────────────────────────── happy path ──────────────────────────


async def test_valid_token_returns_user(make_user_token, fake_jwks_client) -> None:
    settings = _real_settings()
    token = make_user_token(oid="alice", tid="test-tenant", aud="test-client-id")
    user = await require_user(
        authorization=f"Bearer {token}", settings=settings, jwks_client=fake_jwks_client
    )
    assert user.oid == "alice"
    assert user.tid == "test-tenant"
    assert "access_as_user" in user.scp
    # Token is stored but never leaks through repr/str.
    assert "Bearer" not in repr(user)
    assert "Bearer" not in str(user)


# ────────────────────────── negative cases ──────────────────────────


async def test_missing_header_rejected(fake_jwks_client) -> None:
    settings = _real_settings()
    with pytest.raises(HTTPException) as exc:
        await require_user(authorization=None, settings=settings, jwks_client=fake_jwks_client)
    assert exc.value.status_code == 401


async def test_non_bearer_scheme_rejected(fake_jwks_client) -> None:
    settings = _real_settings()
    with pytest.raises(HTTPException) as exc:
        await require_user(
            authorization="Basic dXNlcjpwYXNz", settings=settings, jwks_client=fake_jwks_client
        )
    assert exc.value.status_code == 401


async def test_alg_none_rejected(make_user_token, fake_jwks_client) -> None:
    """alg=none bypass — pyjwt actually refuses to encode with alg=none, so
    we hand-craft a header to simulate."""
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=")
    payload = base64.urlsafe_b64encode(b'{"oid":"x"}').rstrip(b"=")
    bogus = f"{header.decode()}.{payload.decode()}.".encode()
    settings = _real_settings()
    with pytest.raises(HTTPException) as exc:
        await require_user(
            authorization=f"Bearer {bogus.decode()}",
            settings=settings,
            jwks_client=fake_jwks_client,
        )
    assert exc.value.status_code == 401


async def test_wrong_audience_rejected(make_user_token, fake_jwks_client) -> None:
    settings = _real_settings()
    token = make_user_token(aud="not-our-audience")
    with pytest.raises(HTTPException):
        await require_user(
            authorization=f"Bearer {token}",
            settings=settings,
            jwks_client=fake_jwks_client,
        )


async def test_wrong_tenant_rejected(make_user_token, fake_jwks_client) -> None:
    """Token issued for a different tenant must be rejected even if signature passes."""
    settings = _real_settings()
    # Issuer matches expected tenant (otherwise iss check trips first), but tid claim differs.
    token = make_user_token(
        tid="other-tenant",
        iss="https://login.microsoftonline.com/test-tenant/v2.0",
    )
    with pytest.raises(HTTPException):
        await require_user(
            authorization=f"Bearer {token}",
            settings=settings,
            jwks_client=fake_jwks_client,
        )


async def test_expired_token_rejected(make_user_token, fake_jwks_client) -> None:
    settings = _real_settings()
    token = make_user_token(exp_offset_sec=-3600)  # expired an hour ago
    with pytest.raises(HTTPException):
        await require_user(
            authorization=f"Bearer {token}",
            settings=settings,
            jwks_client=fake_jwks_client,
        )


async def test_missing_oid_rejected(make_user_token, fake_jwks_client) -> None:
    """oid is optional in v2 — but the backend rejects 401, never 500."""
    settings = _real_settings()
    token = make_user_token(include_oid=False)
    with pytest.raises(HTTPException) as exc:
        await require_user(
            authorization=f"Bearer {token}",
            settings=settings,
            jwks_client=fake_jwks_client,
        )
    assert exc.value.status_code == 401


# ────────────────────────── leak resistance ──────────────────────────


def test_user_repr_omits_token(make_user_token, rsa_key_pair) -> None:
    from pydantic import SecretStr

    from agentgenesis_api.auth.models import User

    u = User(
        oid="x", tid="t", upn=None, name="N", scp=[],
        raw_token=SecretStr("super-secret-token"),
    )
    for s in (repr(u), str(u), u.model_dump_json()):
        assert "super-secret-token" not in s


def test_user_model_dump_omits_raw_token() -> None:
    from pydantic import SecretStr

    from agentgenesis_api.auth.models import User

    u = User(oid="x", tid="t", raw_token=SecretStr("secret"))
    assert "raw_token" not in u.model_dump()
