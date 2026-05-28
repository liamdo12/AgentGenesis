"""Entra ID JWT validation + OBO token broker + FastAPI dependency."""

from agentgenesis_api.auth.dependency import require_user
from agentgenesis_api.auth.models import STUB_USER, User
from agentgenesis_api.auth.token_broker import (
    ConsentRequiredError,
    TokenBroker,
    TokenBrokerError,
    TokenExpiredError,
)

__all__ = [
    "STUB_USER",
    "ConsentRequiredError",
    "TokenBroker",
    "TokenBrokerError",
    "TokenExpiredError",
    "User",
    "require_user",
]
