"""Path conventions for Claude Code's on-disk session store and our archive.

Claude Code persists every session as a JSONL file at:

    <claude-config>/projects/<encoded-cwd>/<session-id>.jsonl

where ``<encoded-cwd>`` is the absolute working directory with every ``/`` and
``.`` replaced by ``-`` (e.g. ``/Users/me/vf`` -> ``-Users-me-vf``; a worktree
``/repo/.worktrees/x`` -> ``-repo--worktrees-x``). ``claude --resume <id>``
locates a session by reading that file from the project dir derived from cwd.
"""

from __future__ import annotations

import os
from pathlib import Path


def claude_config_root() -> Path:
    """Root of the Claude Code config dir (honors ``CLAUDE_CONFIG_DIR``)."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".claude"


def claude_projects_root() -> Path:
    """Directory holding one sub-dir of session JSONL files per project."""
    return claude_config_root() / "projects"


def encode_project_dir(cwd: str | Path) -> str:
    """Encode an absolute cwd into Claude Code's project-dir name.

    Replaces both ``/`` and ``.`` with ``-`` to match Claude Code's scheme.
    """
    return str(cwd).replace("/", "-").replace(".", "-")


def project_dir(cwd: str | Path) -> Path:
    """Absolute path to the project dir that holds ``cwd``'s sessions."""
    return claude_projects_root() / encode_project_dir(cwd)


def session_file(cwd: str | Path, session_id: str) -> Path:
    """Path where ``session_id``'s JSONL lives for the given ``cwd``."""
    return project_dir(cwd) / f"{session_id}.jsonl"


def find_session_anywhere(session_id: str) -> Path | None:
    """Locate a session JSONL by id across all projects (cwd unknown)."""
    matches = sorted(claude_projects_root().glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def find_latest_session(cwd: str | Path) -> Path | None:
    """Most-recently-modified session JSONL in ``cwd``'s project dir."""
    pdir = project_dir(cwd)
    if not pdir.is_dir():
        return None
    sessions = [p for p in pdir.glob("*.jsonl") if p.is_file()]
    if not sessions:
        return None
    return max(sessions, key=lambda p: p.stat().st_mtime)


def library_home() -> Path:
    """Root of our saved-conversation library (honors ``CCBOOKMARK_HOME``)."""
    override = os.environ.get("CCBOOKMARK_HOME")
    return Path(override).expanduser() if override else Path.home() / ".ccbookmark"


def archive_dir() -> Path:
    """Directory where saved session JSONL copies are stored."""
    return library_home() / "archive"


def index_db_path() -> Path:
    """Path to the SQLite metadata index."""
    return library_home() / "index.db"
