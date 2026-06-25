"""Optional Claude-API summary regeneration.

This is an opt-in extra: the base install does not depend on ``anthropic``.
Install it with ``uv sync --extra summary`` (or ``pip install ccbookmark[summary]``)
and set ``ANTHROPIC_API_KEY``. Without either, summary extraction (the default)
still works with no API key and no cost.
"""

from __future__ import annotations

import os

try:
    import anthropic
except ImportError:  # optional dependency — not installed in the base profile
    anthropic = None  # type: ignore[assignment]

# Per the claude-api guidance, default to the latest Opus; override for cheaper runs.
DEFAULT_MODEL = "claude-opus-4-8"
_MAX_TRANSCRIPT_CHARS = 60_000
_PROMPT = (
    "Summarize this Claude Code coding conversation in 4-6 sentences for someone "
    "deciding whether to resume it. Cover the original goal, what was done, and the "
    "current state. Be concrete and factual; no preamble.\n\n"
    "<transcript>\n{transcript}\n</transcript>"
)


class SummaryError(Exception):
    """Raised when a summary cannot be regenerated via the Claude API."""


def available() -> bool:
    """Whether the optional ``anthropic`` dependency is importable."""
    return anthropic is not None


def regenerate_summary(transcript_text: str, model: str | None = None) -> str:
    """Generate a fresh summary of ``transcript_text`` via the Claude API.

    Raises :class:`SummaryError` if the optional dependency or API key is missing,
    or if the API call fails.
    """
    if anthropic is None:
        raise SummaryError(
            "The 'anthropic' package is not installed. Install it with: uv sync --extra summary"
        )
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SummaryError("ANTHROPIC_API_KEY is not set; cannot regenerate the summary.")

    model = model or os.environ.get("CCBOOKMARK_SUMMARY_MODEL") or DEFAULT_MODEL
    transcript = transcript_text[:_MAX_TRANSCRIPT_CHARS]
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": _PROMPT.format(transcript=transcript)}],
        )
    except (anthropic.APIError, anthropic.APIConnectionError) as exc:
        raise SummaryError(f"Claude API call failed: {exc}") from exc

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise SummaryError("Claude returned an empty summary.")
    return text
