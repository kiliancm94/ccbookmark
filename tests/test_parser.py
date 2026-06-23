from pathlib import Path

from ccbookmark.parser import parse_session

FIXTURE = Path(__file__).parent / "fixtures" / "sample-session.jsonl"


def test_parse_extracts_metadata():
    meta = parse_session(FIXTURE)
    assert meta.session_id == "sample-session"  # falls back to filename stem
    assert meta.title == "Build a log file parser"
    assert meta.cwd == "/tmp/demo-proj"
    assert meta.git_branch == "main"
    assert meta.version == "2.1.0"
    assert meta.slug == "demo-slug"


def test_parse_counts_real_user_prompts_only():
    meta = parse_session(FIXTURE)
    # two text prompts; the tool_result-only user turn is not counted
    assert meta.user_count == 2
    assert meta.assistant_count == 2
    assert meta.first_prompt == "Build me a small parser for log files."


def test_parse_token_totals():
    meta = parse_session(FIXTURE)
    assert meta.total_input_tokens == 150
    assert meta.total_output_tokens == 50


def test_parse_collects_files():
    meta = parse_session(FIXTURE)
    assert "/tmp/demo-proj/parser.py" in meta.files  # from Write tool_use
    assert "/tmp/demo-proj/README.md" in meta.files  # from file attachment


def test_summary_includes_title_and_first_prompt():
    meta = parse_session(FIXTURE)
    assert "Build a log file parser" in meta.summary
    assert "Build me a small parser" in meta.summary


def test_explicit_session_id_overrides_stem():
    meta = parse_session(FIXTURE, session_id="custom-id")
    assert meta.session_id == "custom-id"
