from pathlib import Path

import pytest

from ccbookmark import summarize
from ccbookmark.parser import extract_transcript_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample-session.jsonl"


def test_extract_transcript_text():
    text = extract_transcript_text(FIXTURE)
    assert "user: Build me a small parser for log files." in text
    assert "assistant: Sure, creating it now." in text
    # tool_result-only user turns contribute no text
    assert "tool_result" not in text


def test_extract_transcript_text_respects_max_chars():
    text = extract_transcript_text(FIXTURE, max_chars=20)
    assert len(text) <= 20


def test_regenerate_summary_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    if not summarize.available():
        pytest.skip("anthropic not installed")
    with pytest.raises(summarize.SummaryError):
        summarize.regenerate_summary("user: hi\nassistant: hello")
