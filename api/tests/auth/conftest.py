"""Auth-test fixtures: RSA key pair + token factory + stubbed JWKS client.

`rsa_key_pair` generates a fresh RSA-2048 key per session. `make_user_token`
mints JWTs signed with that private key for arbitrary claim shapes. The
fixture-built `PyJWKClient` replacement serves only the public half so the
auth dependency's signature check passes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass
class RSAKeyPair:
    private_pem: bytes
    public_pem: bytes
    public_key: object  # cryptography RSAPublicKey
    kid: str


@pytest.fixture(scope="session")
def rsa_key_pair() -> RSAKeyPair:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = key.public_key()
    public_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return RSAKeyPair(
        private_pem=private_pem, public_pem=public_pem, public_key=pub, kid="test-kid-1"
    )


@pytest.fixture
def make_user_token(rsa_key_pair):
    """Factory: returns a function that produces a signed JWT with overridable claims."""

    def _make(
        *,
        oid: str = "user-1",
        tid: str = "test-tenant",
        aud: str = "test-client-id",
        iss: str | None = None,
        scopes: tuple[str, ...] = ("access_as_user",),
        exp_offset_sec: int = 3600,
        nbf_offset_sec: int = 0,
        include_oid: bool = True,
        alg: str = "RS256",
        kid: str | None = None,
    ) -> str:
        now = int(time.time())
        claims: dict = {
            "tid": tid,
            "aud": aud,
            "iss": iss or f"https://login.microsoftonline.com/{tid}/v2.0",
            "scp": " ".join(scopes),
            "iat": now,
            "nbf": now + nbf_offset_sec,
            "exp": now + exp_offset_sec,
        }
        if include_oid:
            claims["oid"] = oid
        return jwt.encode(
            claims,
            rsa_key_pair.private_pem,
            algorithm=alg,
            headers={"kid": kid or rsa_key_pair.kid},
        )

    return _make


class _FakeSigningKey:
    def __init__(self, public_key):
        self.key = public_key


class _FakeJWKClient:
    """Stub that returns the test RSA public key regardless of kid lookup."""

    def __init__(self, public_key):
        self._key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._key)


@pytest.fixture
def fake_jwks_client(rsa_key_pair) -> _FakeJWKClient:
    return _FakeJWKClient(rsa_key_pair.public_key)
