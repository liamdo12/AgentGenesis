"""Application settings loaded from environment / .env file."""

from pathlib import Path
from typing import Literal

from pydantic import HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    data_dir: Path = Path("./data")
    environment: Literal["dev", "test", "prod"] = "dev"

    # Microsoft Entra ID (Phase 1)
    # Required in non-stub mode. The validator below tolerates blanks when
    # use_stub_nodes is true (CI / design QA).
    entra_tenant_id: str = ""
    entra_client_id: str = ""                              # GUID; v2 token audience
    entra_client_secret: SecretStr = SecretStr("")         # for OBO exchange
    graph_delegated_scopes: tuple[str, ...] = (
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/OnlineMeetingRecording.Read.All",
        "https://graph.microsoft.com/OnlineMeetingTranscript.Read.All",
    )

    # Microsoft Teams MCP (DEPRECATED — deleted in Phase 4 of the SSO plan).
    # Kept here so existing TeamsMCPClient + tests keep compiling during the
    # phased rollout. Once Phase 4 ships, this block goes away.
    teams_mcp_url: HttpUrl = HttpUrl("http://localhost:3000/mcp")
    teams_mcp_auth_token: SecretStr | None = None
    mcp_tool_list_recordings: str = "list_meeting_recordings"
    mcp_tool_get_transcript: str = "get_meeting_transcript"
    mcp_tool_get_recording: str = "get_meeting_recording"

    # Anthropic
    # Required for Phase 6 (Claude synthesis). Earlier phases boot fine without it
    # if a job is submitted with synthesis disabled — for v1 we just require it
    # so the failure mode is "missing key at boot", not "500 mid-pipeline".
    anthropic_api_key: SecretStr
    claude_model: str = "claude-sonnet-4-6"

    # Frame extraction
    frame_interval_sec: int = 30
    chunk_window_sec: int = 600
    max_parallel_ffmpeg: int = 4
    min_useful_frames: int = 3

    # Synthesis (Phase 6)
    synth_max_input_tokens: int = 150_000
    synth_chunk_overlap_sec: int = 30
    synth_max_frames_in_context: int = 12
    synth_max_cost_usd: float = 1.00
    synth_claude_retries: int = 3

    # Graph / runs
    max_concurrent_runs: int = 2
    # When true (default), the graph wires real node implementations against
    # MCP/Claude/ffmpeg. Tests can flip to false (AG_USE_STUB_NODES=1) to drive
    # the run lifecycle without any external services.
    use_stub_nodes: bool = False

    # Phase 4 — recording fetch
    recording_download_timeout_sec: int = 1800  # 30 min hard cap
    recording_chunk_bytes: int = 1 << 20  # 1 MiB streaming chunks

    # Persistence (Phase 1 — frontend integration plan)
    # Default sqlite + aiosqlite for dev/test. Override with AG_DATABASE_URL
    # to point at SQL Server (`mssql+aioodbc://...`) — prod also requires
    # out-of-band DDL provisioning; see api/README.md.
    database_url: str = "sqlite+aiosqlite:///./data/agentgenesis.db"

    # Observability
    log_format: str = "console"  # "console" | "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AG_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_auth_mode(self) -> "Settings":
        # Hard guardrail per red-team Finding 6: stub auth must not be enabled
        # in production, even if the env var is accidentally set.
        if self.use_stub_nodes and self.environment == "prod":
            raise ValueError(
                "use_stub_nodes=True is refused when environment='prod'. "
                "Stub auth bypasses Entra ID validation and must never run in production."
            )
        # When not in stub mode, real Entra creds are required.
        if not self.use_stub_nodes:
            missing = [
                name for name, val in (
                    ("AG_ENTRA_TENANT_ID", self.entra_tenant_id),
                    ("AG_ENTRA_CLIENT_ID", self.entra_client_id),
                    ("AG_ENTRA_CLIENT_SECRET", self.entra_client_secret.get_secret_value()),
                )
                if not val
            ]
            if missing:
                raise ValueError(
                    f"Entra ID config required when use_stub_nodes is false. Missing: {missing}"
                )
        return self
