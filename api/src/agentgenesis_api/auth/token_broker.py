"""On-Behalf-Of token broker.

Exchanges a validated user JWT for a Graph-scoped delegated access token via
the Microsoft Entra OBO flow. Caches exchanged tokens per `(oid, scope_set)`
with a 60s safety margin under the Entra-reported `expires_in`.

Distinct typed errors for the three Entra failure modes the frontend handles
differently:
  - `TokenExpiredError`     → 401 "session expired"; frontend redirects to login.
  - `ConsentRequiredError`  → 401 with `claims` param; frontend calls
                              `acquireTokenPopup({ claims })`. NEVER conflate
                              with "session expired" (loops on first-use
                              consent gaps). Per red-team Finding 5.
  - `TokenBrokerError`      → 503 transient; caller can retry.

Single-flight dedup under a single `asyncio.Lock` ensures concurrent callers
for the same `(oid, scopes)` produce at most one OBO request.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.auth.token_broker")

_OBO_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_SAFETY_MARGIN_SEC = 60.0
_RETRY_BASE_SEC = 1.0
_RETRY_ATTEMPTS = 3


class TokenBrokerError(RuntimeError):
    """Transient OBO failure (5xx, network). Caller maps to 503."""


class TokenExpiredError(RuntimeError):
    """User's session is invalid (invalid_grant without consent suberror)."""


class ConsentRequiredError(RuntimeError):
    """User must satisfy a claims challenge before OBO can succeed.

    Frontend passes `claims` to `acquireTokenPopup({ claims })` instead of
    plain re-login (which doesn't fix the consent gap).
    """

    def __init__(self, claims: str | None):
        super().__init__(f"consent required (claims={claims!r})")
        self.claims = claims


@dataclass
class _CachedToken:
    token: str
    expires_at: float  # monotonic seconds


class TokenBroker:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(timeout=10.0)
        self._cache: dict[tuple[str, tuple[str, ...]], _CachedToken] = {}
        self._inflight: dict[tuple[str, tuple[str, ...]], asyncio.Future[str]] = {}
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        # Cancel any inflight futures so awaiters don't hang on a closed loop.
        async with self._lock:
            for fut in self._inflight.values():
                if not fut.done():
                    fut.cancel()
            self._inflight.clear()
            self._cache.clear()
        await self._client.aclose()

    async def acquire_graph_token(self, user: User, scopes: tuple[str, ...]) -> str:
        if self._settings.use_stub_nodes:
            return "stub-graph-token"

        key = (user.oid, scopes)
        now = time.monotonic()

        async with self._lock:
            cached = self._cache.get(key)
            if cached and cached.expires_at > now:
                return cached.token
            fut = self._inflight.get(key)
            if fut is not None:
                do_exchange = False
            else:
                fut = asyncio.get_running_loop().create_future()
                self._inflight[key] = fut
                do_exchange = True

        if do_exchange:
            try:
                token, expires_in = await self._exchange(user, scopes)
            except Exception as e:
                async with self._lock:
                    self._inflight.pop(key, None)
                if not fut.done():
                    fut.set_exception(e)
                    # Consume so asyncio doesn't warn "exception never retrieved"
                    # when no sibling caller awaits this future.
                    fut.exception()
                raise
            async with self._lock:
                self._cache[key] = _CachedToken(
                    token=token,
                    expires_at=time.monotonic() + max(0.0, expires_in - _SAFETY_MARGIN_SEC),
                )
                self._inflight.pop(key, None)
            if not fut.done():
                fut.set_result(token)
            return token

        return await fut

    async def _exchange(self, user: User, scopes: tuple[str, ...]) -> tuple[str, float]:
        url = (
            f"https://login.microsoftonline.com/{self._settings.entra_tenant_id}"
            "/oauth2/v2.0/token"
        )
        body = {
            "grant_type": _OBO_GRANT,
            "client_id": self._settings.entra_client_id,
            "client_secret": self._settings.entra_client_secret.get_secret_value(),
            "assertion": user.raw_token.get_secret_value(),
            "requested_token_use": "on_behalf_of",
            "scope": " ".join(scopes),
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        last_err: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                resp = await self._client.post(url, content=urlencode(body), headers=headers)
            except httpx.HTTPError as e:
                last_err = e
                await asyncio.sleep(_RETRY_BASE_SEC * (2**attempt))
                continue

            if resp.status_code >= 500:
                last_err = TokenBrokerError(f"OBO {resp.status_code}: {resp.text[:200]}")
                await asyncio.sleep(_RETRY_BASE_SEC * (2**attempt))
                continue

            data = resp.json()
            if resp.status_code >= 400:
                error = data.get("error", "")
                error_desc = data.get("error_description", "")
                claims = data.get("claims")
                suberror = data.get("suberror", "")
                log.info(
                    "obo.error",
                    oid=user.oid,
                    error=error,
                    suberror=suberror,
                    has_claims=bool(claims),
                )
                if error in ("interaction_required", "consent_required") or suberror == "consent_required":
                    raise ConsentRequiredError(claims=claims)
                if error == "invalid_grant":
                    raise TokenExpiredError(error_desc[:200])
                raise RuntimeError(f"OBO config error {error}: {error_desc[:200]}")

            return data["access_token"], float(data.get("expires_in", 3600))

        raise TokenBrokerError(
            f"OBO failed after {_RETRY_ATTEMPTS} attempts: {last_err}"
        )


# Convenience helper for the per-process boot guard — exposed so future code
# (or a /readyz endpoint) can introspect token state without touching internals.
def cached_token_count(broker: TokenBroker) -> int:
    return len(broker._cache)


# Keep SecretStr import referenced for downstream type-checkers.
_ = SecretStr
