"""Tests for the OBO token broker.

Covers: cache hit, cache miss → exchange, expiry-respect, single-flight
dedup, error mapping (TokenExpiredError vs ConsentRequiredError vs
TokenBrokerError), and graceful shutdown.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
from pydantic import SecretStr

from agentgenesis_api.auth import (
    ConsentRequiredError,
    TokenBroker,
    TokenBrokerError,
    TokenExpiredError,
    User,
)
from agentgenesis_api.config import Settings


def _real_settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        environment="dev",
        entra_tenant_id="t-1",
        entra_client_id="c-1",
        entra_client_secret="s-1",
        anthropic_api_key="x",
        use_stub_nodes=False,
    )


def _user(oid: str = "alice") -> User:
    return User(oid=oid, tid="t-1", raw_token=SecretStr("user-jwt"))


_TOKEN_URL = "https://login.microsoftonline.com/t-1/oauth2/v2.0/token"
_SCOPES = ("https://graph.microsoft.com/User.Read",)


@pytest.fixture
def broker():
    b = TokenBroker(_real_settings())
    yield b
    asyncio.get_event_loop().run_until_complete(b.aclose()) if False else None  # cleanup via explicit close below


@respx.mock
async def test_stub_mode_returns_literal() -> None:
    settings = Settings(use_stub_nodes=True, environment="test", anthropic_api_key="x")  # type: ignore[call-arg]
    b = TokenBroker(settings)
    try:
        result = await b.acquire_graph_token(_user(), _SCOPES)
        assert result == "stub-graph-token"
    finally:
        await b.aclose()


@respx.mock
async def test_first_call_exchanges_then_caches() -> None:
    route = respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "graph-tkn", "expires_in": 3600}
        )
    )
    b = TokenBroker(_real_settings())
    try:
        first = await b.acquire_graph_token(_user(), _SCOPES)
        second = await b.acquire_graph_token(_user(), _SCOPES)
        assert first == "graph-tkn"
        assert second == "graph-tkn"
        assert route.call_count == 1
    finally:
        await b.aclose()


@respx.mock
async def test_cache_expires_with_safety_margin() -> None:
    route = respx.post(_TOKEN_URL).mock(
        # expires_in below the 60s safety margin → cache is born expired.
        return_value=httpx.Response(
            200, json={"access_token": "graph-tkn", "expires_in": 30}
        )
    )
    b = TokenBroker(_real_settings())
    try:
        await b.acquire_graph_token(_user(), _SCOPES)
        await b.acquire_graph_token(_user(), _SCOPES)
        assert route.call_count == 2
    finally:
        await b.aclose()


@respx.mock
async def test_consent_required_maps_to_typed_error() -> None:
    respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": "interaction_required",
                "error_description": "AADSTS50079: …",
                "claims": '{"access_token":{"acr":{"essential":true}}}',
            },
        )
    )
    b = TokenBroker(_real_settings())
    try:
        with pytest.raises(ConsentRequiredError) as exc:
            await b.acquire_graph_token(_user(), _SCOPES)
        assert "essential" in (exc.value.claims or "")
    finally:
        await b.aclose()


@respx.mock
async def test_invalid_grant_maps_to_token_expired() -> None:
    respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "user session expired"},
        )
    )
    b = TokenBroker(_real_settings())
    try:
        with pytest.raises(TokenExpiredError):
            await b.acquire_graph_token(_user(), _SCOPES)
    finally:
        await b.aclose()


@respx.mock
async def test_5xx_then_success_retries() -> None:
    route = respx.post(_TOKEN_URL).mock(
        side_effect=[
            httpx.Response(503, text="busy"),
            httpx.Response(200, json={"access_token": "graph-tkn", "expires_in": 3600}),
        ]
    )
    b = TokenBroker(_real_settings())
    try:
        result = await b.acquire_graph_token(_user(), _SCOPES)
        assert result == "graph-tkn"
        assert route.call_count == 2
    finally:
        await b.aclose()


@respx.mock
async def test_5xx_persistent_raises_broker_error() -> None:
    respx.post(_TOKEN_URL).mock(return_value=httpx.Response(503, text="busy"))
    settings = _real_settings()
    b = TokenBroker(settings)
    try:
        with pytest.raises(TokenBrokerError):
            # Speed the test: shrink the retry sleep.
            import agentgenesis_api.auth.token_broker as tb
            original = tb._RETRY_BASE_SEC
            tb._RETRY_BASE_SEC = 0.0
            try:
                await b.acquire_graph_token(_user(), _SCOPES)
            finally:
                tb._RETRY_BASE_SEC = original
    finally:
        await b.aclose()


@respx.mock
async def test_concurrent_callers_share_one_exchange() -> None:
    """10 concurrent acquires for the same (oid, scopes) → 1 OBO request."""
    route = respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "graph-tkn", "expires_in": 3600}
        )
    )
    b = TokenBroker(_real_settings())
    try:
        results = await asyncio.gather(
            *(b.acquire_graph_token(_user("alice"), _SCOPES) for _ in range(10))
        )
        assert all(r == "graph-tkn" for r in results)
        assert route.call_count == 1
    finally:
        await b.aclose()


@respx.mock
async def test_different_scopes_separate_cache() -> None:
    respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "graph-tkn", "expires_in": 3600}
        )
    )
    b = TokenBroker(_real_settings())
    try:
        await b.acquire_graph_token(_user(), ("https://graph.microsoft.com/User.Read",))
        await b.acquire_graph_token(_user(), ("https://graph.microsoft.com/OnlineMeetingRecording.Read.All",))
        # 2 distinct scope sets → 2 exchanges.
        assert len(b._cache) == 2
    finally:
        await b.aclose()


@respx.mock
async def test_shutdown_clears_caches() -> None:
    respx.post(_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "graph-tkn", "expires_in": 3600}
        )
    )
    b = TokenBroker(_real_settings())
    await b.acquire_graph_token(_user(), _SCOPES)
    assert len(b._cache) == 1
    await b.aclose()
    assert b._cache == {}
    assert b._inflight == {}
