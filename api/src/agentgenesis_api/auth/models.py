"""User model returned by `require_user`.

`raw_token` is a SecretStr with explicit `repr=False` + overridden `__repr__`
so a stray `print(user)`, FastAPI exception traceback, or structlog frame-locals
dump cannot leak the JWT. Per red-team Finding 14.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class User(BaseModel):
    oid: str                                  # Entra object ID; stable per user
    tid: str                                  # Tenant ID
    upn: str | None = None
    name: str | None = None
    scp: list[str] = Field(default_factory=list)
    # SecretStr redacts in pydantic repr; explicit exclude protects model_dump;
    # __repr__ override below covers Python-level repr / print / traceback.
    raw_token: SecretStr = Field(exclude=True, repr=False)

    model_config = ConfigDict(frozen=True)

    def __repr__(self) -> str:
        return f"User(oid={self.oid!r}, tid={self.tid!r}, name={self.name!r})"

    def __str__(self) -> str:
        return self.__repr__()


# Deterministic stub user used when Settings.use_stub_nodes is true.
# IMPORTANT: never returned in production — the Settings model_validator refuses
# to boot in prod with stub mode enabled (Phase 1 hard guard).
STUB_USER = User(
    oid="stub-user",
    tid="stub-tenant",
    upn="stub@example.com",
    name="Stub User",
    scp=["access_as_user"],
    raw_token=SecretStr("stub-token"),
)
