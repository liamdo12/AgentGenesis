"""Claude synthesis pipeline (Phase 6).

merge_context → claude_summary → claude_draft_stories. Token preflight picks
single-shot vs map-reduce based on `synth_max_input_tokens`.
"""

from agentgenesis_api.synthesis.claude_client import ClaudeClient, ClaudeError
from agentgenesis_api.synthesis.schemas import MultimodalContext, TimeWindow

__all__ = ["ClaudeClient", "ClaudeError", "MultimodalContext", "TimeWindow"]
