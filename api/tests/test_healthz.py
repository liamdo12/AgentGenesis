"""Phase 1 smoke: /healthz returns ok, and the app boots."""

from fastapi.testclient import TestClient

from agentgenesis_api.config import Settings
from agentgenesis_api.main import create_app


def test_healthz(env_setup) -> None:
    app = create_app(Settings())  # type: ignore[call-arg]
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_settings_require_env(monkeypatch) -> None:
    """Missing required env vars must fail at Settings(), not silently."""
    monkeypatch.delenv("AG_TEAMS_MCP_URL", raising=False)
    monkeypatch.delenv("AG_ANTHROPIC_API_KEY", raising=False)

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)  # type: ignore[call-arg]
    msg = str(exc.value)
    assert "teams_mcp_url" in msg.lower() or "anthropic_api_key" in msg.lower()
