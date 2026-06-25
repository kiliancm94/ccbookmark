"""Stream-parse a Claude Code session JSONL into summary metadata.

Files can be many MB, so records are read line-by-line and malformed lines are
skipped. ``parse_session`` extracts the workspace metadata, message/token
counts, touched files, and an extracted (not generated) summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_FILE_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}
_MAX_FIRST_PROMPT = 2000


@dataclass
class SessionMeta:
    """Extracted metadata for one saved conversation."""

    session_id: str
    title: str = ""
    slug: str = ""
    summary: str = ""
    first_prompt: str = ""
    cwd: str = ""
    git_branch: str = ""
    version: str = ""
    user_count: int = 0
    assistant_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    first_ts: str = ""
    last_ts: str = ""
    files: list[str] = field(default_factory=list)


def _text_from_content(content: object) -> str:
    """Return the human text of a message ``content`` (string or block array)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p).strip()
    return ""


def _iter_records(path: Path):
    """Yield parsed JSON objects from a JSONL file, skipping bad lines."""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_session(path: Path, session_id: str | None = None) -> SessionMeta:
    """Parse the session JSONL at ``path`` into a :class:`SessionMeta`."""
    sid = session_id or path.stem
    meta = SessionMeta(session_id=sid)
    files: list[str] = []
    seen_files: set[str] = set()
    ai_title = ""
    compact_summary = ""

    for rec in _iter_records(path):
        rtype = rec.get("type")

        # Workspace / version metadata — keep the latest non-empty value seen.
        meta.cwd = rec.get("cwd") or meta.cwd
        meta.git_branch = rec.get("gitBranch") or meta.git_branch
        meta.version = rec.get("version") or meta.version
        meta.slug = rec.get("slug") or meta.slug
        if not meta.session_id:
            meta.session_id = rec.get("sessionId") or meta.session_id

        ts = rec.get("timestamp")
        if ts:
            if not meta.first_ts:
                meta.first_ts = ts
            meta.last_ts = ts

        if rtype == "ai-title":
            ai_title = rec.get("aiTitle") or ai_title
        elif rtype == "summary":  # legacy session summary record
            compact_summary = rec.get("summary") or compact_summary
        elif rtype == "system":
            if rec.get("subtype") == "compact_boundary" and rec.get("content"):
                compact_summary = str(rec["content"])
        elif rtype == "user":
            content = rec.get("message", {}).get("content")
            text = _text_from_content(content)
            if text:  # a real prompt, not a tool_result-only turn
                meta.user_count += 1
                if not meta.first_prompt:
                    meta.first_prompt = text[:_MAX_FIRST_PROMPT]
        elif rtype == "assistant":
            meta.assistant_count += 1
            usage = rec.get("message", {}).get("usage") or {}
            meta.total_input_tokens += int(usage.get("input_tokens") or 0)
            meta.total_output_tokens += int(usage.get("output_tokens") or 0)
            for block in rec.get("message", {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    if block.get("name") in _FILE_TOOLS:
                        fp = (block.get("input") or {}).get("file_path")
                        if fp and fp not in seen_files:
                            seen_files.add(fp)
                            files.append(fp)
        elif rtype == "attachment":
            att = rec.get("attachment") or {}
            if att.get("type") == "file":
                fp = att.get("filename")
                if fp and fp not in seen_files:
                    seen_files.add(fp)
                    files.append(fp)

    meta.files = files
    meta.title = ai_title or _first_line(meta.first_prompt) or sid
    meta.summary = _build_summary(meta.title, compact_summary, meta.first_prompt)
    return meta


def extract_transcript_text(path: Path, max_chars: int = 60_000) -> str:
    """Concatenate the human-readable user/assistant text of a session.

    Used to feed an optional Claude-API summary regeneration. Streams the JSONL
    and stops once ``max_chars`` is reached.
    """
    parts: list[str] = []
    total = 0
    for rec in _iter_records(path):
        if rec.get("type") not in ("user", "assistant"):
            continue
        text = _text_from_content(rec.get("message", {}).get("content"))
        if not text:
            continue
        chunk = f"{rec['type']}: {text}"
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n\n".join(parts)[:max_chars]


def _first_line(text: str, limit: int = 120) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line[:limit]


def _build_summary(title: str, compact: str, first_prompt: str) -> str:
    """Assemble a readable summary from the pieces available in the JSONL."""
    parts: list[str] = []
    if title:
        parts.append(title)
    if compact:
        parts.append(compact.strip())
    elif first_prompt:
        parts.append(f"First request: {first_prompt.strip()}")
    return "\n\n".join(parts).strip()
