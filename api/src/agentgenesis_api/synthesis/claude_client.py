"""Thin async wrapper around the Anthropic SDK for structured-JSON synthesis.

The wrapper takes a Pydantic model class and returns a validated instance.
On invalid JSON, it retries once with a repair prompt that includes the
specific validation error. On transient API errors, exponential backoff up to
`synth_claude_retries`.
"""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import anthropic
from anthropic.types import MessageParam
from pydantic import BaseModel, ValidationError

from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger

if TYPE_CHECKING:
    from agentgenesis_api.services.protocols import ChatChunk

log = get_logger("agentgenesis_api.synthesis.claude_client")

T = TypeVar("T", bound=BaseModel)

_TRANSIENT_ERRORS = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
)


class ClaudeError(RuntimeError):
    """Raised when Claude failed in a non-retryable way."""


class ClaudeClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        api_key = settings.anthropic_api_key.get_secret_value()
        self._raw = anthropic.AsyncAnthropic(api_key=api_key)

    async def aclose(self) -> None:
        await self._raw.close()

    async def structured_json(
        self,
        *,
        system: str,
        user_text: str,
        frame_paths: list[Path] | None = None,
        schema: type[T],
        max_tokens: int = 4096,
    ) -> T:
        """Call Claude expecting a JSON response, validate against `schema`."""
        content: list[dict] = []
        for fp in frame_paths or []:
            content.append(_image_block(fp))
        content.append({"type": "text", "text": user_text})

        messages: list[MessageParam] = [{"role": "user", "content": content}]
        repair_hint: str | None = None

        for repair_attempt in range(2):  # 0 = first try; 1 = one repair retry
            sys_prompt = system if repair_hint is None else system + "\n\n" + repair_hint
            text = await self._call_with_retry(messages, sys_prompt, max_tokens)
            try:
                payload = _extract_first_json_object(text)
                return schema.model_validate(payload)
            except (ValidationError, ValueError) as e:
                if repair_attempt == 1:
                    raise ClaudeError(f"Claude returned invalid JSON after repair: {e}") from e
                repair_hint = (
                    "Your previous response was not valid JSON for the required schema: "
                    f"{e}. Respond again with ONLY a single JSON object that matches "
                    "the schema."
                )
                log.warning("claude.repair_retry", error=str(e)[:200])
        raise ClaudeError("unreachable")

    async def stream_chat(
        self, *, system: str, user_text: str, max_tokens: int = 4096
    ) -> AsyncIterator[ChatChunk]:
        """Stream a chat turn from Claude. Yields {type: text} per delta, and
        {type: stories, stories, removed_ids} when an `ag-stories` fenced
        JSON block closes. Tolerates fences split across deltas.
        """
        from agentgenesis_api.services.chat import LlmStoriesReviseOutput

        accum = ""
        in_fence = False
        fence_start: int | None = None
        async with self._raw.messages.stream(
            model=self._settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_text}],
        ) as stream:
            async for delta in stream.text_stream:
                accum += delta
                # Emit text deltas verbatim — the parser inspects `accum`.
                yield {"type": "text", "text": delta}

                # Track fence open/close in the accumulated buffer.
                while True:
                    if not in_fence:
                        idx = accum.find("```ag-stories", 0 if fence_start is None else fence_start)
                        if idx < 0:
                            break
                        in_fence = True
                        fence_start = idx + len("```ag-stories")
                        continue
                    end = accum.find("```", fence_start or 0)
                    if end < 0:
                        break
                    payload = accum[fence_start:end].strip()
                    try:
                        obj = json.loads(payload)
                        revised = LlmStoriesReviseOutput.model_validate(obj)
                        yield {
                            "type": "stories",
                            "stories": revised.model_dump(),
                            "removed_ids": revised.removed_ids,
                        }
                    except (json.JSONDecodeError, ValidationError) as e:
                        log.warning("claude.stream_chat.bad_fence", error=str(e)[:200])
                    in_fence = False
                    fence_start = end + 3

    async def _call_with_retry(
        self, messages: list[MessageParam], system: str, max_tokens: int
    ) -> str:
        for attempt in range(self._settings.synth_claude_retries):
            try:
                resp = await self._raw.messages.create(
                    model=self._settings.claude_model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return "".join(b.text for b in resp.content if b.type == "text")
            except _TRANSIENT_ERRORS as e:
                if attempt == self._settings.synth_claude_retries - 1:
                    raise ClaudeError(f"Claude transient failure after retries: {e}") from e
                backoff = 2**attempt
                log.warning("claude.transient_retry", attempt=attempt, backoff=backoff)
                await asyncio.sleep(backoff)
        raise ClaudeError("unreachable")


def _image_block(path: Path) -> dict:
    """Build an Anthropic image content block from a local file."""
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    media_type = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _extract_first_json_object(text: str) -> dict:
    """Find the first balanced JSON object in `text`. Tolerant of code fences."""
    s = text.strip()
    # Strip code fences if present.
    if s.startswith("```"):
        s = s.split("```", 2)[1] if "```" in s[3:] else s
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    # Scan for the first balanced { ... } block.
    depth = 0
    start = None
    for i, ch in enumerate(s):
        if ch == "{":
            if start is None:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return json.loads(s[start : i + 1])
    raise ValueError("no JSON object found in response")
