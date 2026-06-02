"""FastAPI dependency that validates an Entra ID Bearer token.

Validation pipeline:
  1. Settings → stub mode short-circuit (test/CI only; refused in prod).
  2. Strip "Bearer " prefix.
  3. Reject anything that's not RS256.
  4. PyJWKClient looks up the signing key by `kid` (cached, lifespan=1h).
  5. jwt.decode with explicit audience (= client_id GUID), issuer (v2), required
     claims, leeway=30s for clock skew.
  6. tid double-check (defensive across token-version changes).
  7. oid presence check — reject 401 if missing (don't 500). Per red-team
     Security F5.

Every failure mode returns 401 with the same body `{ "detail": "unauthorized" }`
so attackers can't distinguish causes. Per red-team Finding from Security
Adversary F8 (auth-vs-transport).
"""

from __future__ import annotations

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient
from pydantic import SecretStr

from agentgenesis_api.auth.models import STUB_USER, User
from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.auth")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


def _get_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or Settings()  # type: ignore[call-arg]


def _get_jwks_client(request: Request) -> PyJWKClient | None:
    # `getattr` with a default so missing-state doesn't raise AttributeError —
    # require_user short-circuits on stub_nodes before this is needed, but a
    # misconfigured lifespan was producing confusing 500s.
    return getattr(request.app.state, "jwks_client", None)


def build_jwks_client(settings: Settings) -> PyJWKClient:
    """Construct the JWKS client. Attached to app.state at startup."""
    uri = f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys"
    return PyJWKClient(uri, cache_keys=True, lifespan=3600, max_cached_keys=16)


async def require_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(_get_settings),  # noqa: B008 — FastAPI canonical
    jwks_client: PyJWKClient | None = Depends(_get_jwks_client),  # noqa: B008
) -> User:
    if settings.use_stub_nodes:
        return STUB_USER
    if jwks_client is None:
        # Real-auth mode but the lifespan didn't attach a JWKS client.
        # Surface a clear 500 rather than the cryptic AttributeError.
        log.error("auth.misconfigured", reason="jwks_client missing on app.state")
        raise _UNAUTHORIZED

    if not authorization:
        raise _UNAUTHORIZED
    token = _strip_bearer(authorization)
    if token is None:
        raise _UNAUTHORIZED

    # Algorithm gate FIRST so a forged token with alg=none / HS256 is rejected
    # before any JWKS lookup. Per red-team Finding (alg=none bypass).
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise _UNAUTHORIZED from None
    if header.get("alg") != "RS256":
        raise _UNAUTHORIZED

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            # v2 access tokens: aud = client_id GUID. Per red-team Finding 3.
            audience=settings.entra_client_id,
            issuer=f"https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0",
            options={"require": ["aud", "iss", "exp", "nbf", "iat"]},
            leeway=30,
        )
    except jwt.PyJWTError as e:
        log.info("auth.reject", reason=type(e).__name__)
        raise _UNAUTHORIZED from None
    except Exception as e:
        # JWKS network / parse failure. Surfaces as 401 deliberately — we
        # cannot validate so we cannot accept. Log distinctly so operators
        # can tell "Entra discovery is down" from "user token is bad".
        log.warning("auth.jwks_fetch_failed", error=str(e)[:200])
        raise _UNAUTHORIZED from None

    # Defensive tid cross-check after iss — historically the discriminator
    # has changed across token versions.
    if claims.get("tid") != settings.entra_tenant_id:
        raise _UNAUTHORIZED

    # `oid` is optional in v2 access tokens unless added as an optional claim
    # in the app manifest (Phase 1 setup doc step 5.2). If missing → 401, never
    # KeyError → 500. Per red-team Security F5.
    oid = claims.get("oid")
    if not oid:
        log.info("auth.reject", reason="missing_oid")
        raise _UNAUTHORIZED

    scp_raw = claims.get("scp") or ""
    return User(
        oid=oid,
        tid=claims["tid"],
        upn=claims.get("upn"),
        name=claims.get("name"),
        scp=scp_raw.split() if scp_raw else [],
        raw_token=SecretStr(token),
    )


def _strip_bearer(authorization: str) -> str | None:
    parts = authorization.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]
