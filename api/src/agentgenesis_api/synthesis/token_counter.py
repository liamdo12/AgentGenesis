"""Token estimation for Claude budget preflight.

We don't ship a model-accurate tokenizer. Use a conservative heuristic
(`len(text) / 3.5` for English-leaning content) and add a fixed cost per
vision frame as documented by Anthropic.

The number is only used as an *upper bound* to decide map-reduce vs
single-shot. The actual call's usage is logged after the fact.
"""

_CHARS_PER_TOKEN_ESTIMATE = 3.5
_TOKENS_PER_VISION_IMAGE = 1600  # Anthropic published estimate, "high" detail


def estimate_text_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text) / _CHARS_PER_TOKEN_ESTIMATE) + 1


def estimate_vision_tokens(image_count: int) -> int:
    return image_count * _TOKENS_PER_VISION_IMAGE


def estimate_total_tokens(text_parts: list[str], image_count: int) -> int:
    return sum(estimate_text_tokens(t) for t in text_parts) + estimate_vision_tokens(image_count)
