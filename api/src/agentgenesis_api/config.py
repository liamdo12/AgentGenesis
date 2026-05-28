"""Application settings loaded from environment / .env file."""

from pathlib import Path

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    data_dir: Path = Path("./data")

    # Microsoft Teams MCP
    teams_mcp_url: HttpUrl
    teams_mcp_auth_token: SecretStr | None = None
    # Tool names are server-specific. Overridable so we can swap MCP servers
    # without touching code.
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

    # Observability
    log_format: str = "console"  # "console" | "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AG_",
        extra="ignore",
    )
