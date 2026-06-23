"""High-level operations: save / list / show / restore / export / delete.

This is the single source of truth shared by the CLI and the MCP server.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import paths, store
from .parser import SessionMeta, parse_session


class SaveError(Exception):
    """Raised when an operation cannot be completed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_live_session(session_id: str | None, cwd: str | None) -> tuple[str, Path]:
    """Find the live session JSONL to save and return ``(session_id, path)``."""
    if session_id:
        path = paths.find_session_anywhere(session_id)
        if path is None:
            raise SaveError(f"No session found with id {session_id!r}.")
        return session_id, path
    target_cwd = cwd or os.getcwd()
    path = paths.find_latest_session(target_cwd)
    if path is None:
        raise SaveError(f"No sessions found for cwd {target_cwd!r}. Pass an explicit session id.")
    return path.stem, path


def save(
    session_id: str | None = None, cwd: str | None = None, tags: list[str] | None = None
) -> SessionMeta:
    """Archive a live session JSONL and index its metadata.

    With no ``session_id`` the most recently modified session in ``cwd`` (or the
    process cwd) is saved.
    """
    sid, live_path = _resolve_live_session(session_id, cwd)
    meta = parse_session(live_path, session_id=sid)

    paths.archive_dir().mkdir(parents=True, exist_ok=True)
    archive_path = paths.archive_dir() / f"{sid}.jsonl"
    shutil.copy2(live_path, archive_path)

    store.upsert(
        meta,
        project_dir=paths.encode_project_dir(meta.cwd) if meta.cwd else "",
        archive_path=str(archive_path),
        tags=tags or [],
        saved_at=_now(),
    )
    return meta


def list_saved(
    query: str | None = None, tags: list[str] | None = None, limit: int = 50
) -> list[dict]:
    """List saved conversations, newest first."""
    return store.search(query=query, tags=tags, limit=limit)


def list_live(cwd: str | None = None, limit: int = 50) -> list[dict]:
    """List live Claude Code sessions available to save, newest first.

    With ``cwd`` only that project's sessions are listed; otherwise every
    project's sessions are scanned. Each entry is lightweight metadata parsed
    from the session JSONL plus whether it is already saved in the library.
    """
    if cwd:
        pdirs = [paths.project_dir(cwd)]
    else:
        root = paths.claude_projects_root()
        pdirs = [p for p in root.glob("*") if p.is_dir()] if root.is_dir() else []

    files = [f for pdir in pdirs if pdir.is_dir() for f in pdir.glob("*.jsonl")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    rows: list[dict] = []
    for path in files[:limit]:
        meta = parse_session(path)
        rows.append(
            {
                "session_id": meta.session_id,
                "title": meta.title,
                "cwd": meta.cwd,
                "git_branch": meta.git_branch,
                "user_count": meta.user_count,
                "assistant_count": meta.assistant_count,
                "last_ts": meta.last_ts,
                "saved": store.get(meta.session_id) is not None,
            }
        )
    return rows


def show(session_id: str) -> dict:
    """Return the full index record for a saved conversation."""
    row = store.get(session_id)
    if row is None:
        raise SaveError(f"No saved conversation with id {session_id!r}.")
    return row


def _archived_path(row: dict) -> Path:
    path = Path(row["archive_path"])
    if not path.is_file():
        raise SaveError(f"Archived JSONL is missing: {path}")
    return path


def restore(session_id: str) -> dict:
    """Copy the archived JSONL back to its original project dir for resume.

    Returns a dict with the destination and the ready-to-run resume command.
    """
    row = show(session_id)
    src = _archived_path(row)
    cwd = row["cwd"]
    if not cwd:
        raise SaveError("Saved session has no recorded cwd; cannot restore.")
    dest = paths.session_file(cwd, session_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    restored = not dest.exists()
    if restored:
        shutil.copy2(src, dest)
    return {
        "session_id": session_id,
        "cwd": cwd,
        "destination": str(dest),
        "restored": restored,
        "command": f"cd {cwd} && claude --resume {session_id}",
    }


def export(session_id: str, target_cwd: str, new_id: bool = False) -> dict:
    """Copy a saved conversation into another project so it resumes there.

    Rewrites each record's ``cwd`` to ``target_cwd``. When ``new_id`` is set, a
    fresh session id is assigned (rewriting ``sessionId`` and the filename) to
    avoid colliding with an existing session in the target project.
    """
    row = show(session_id)
    src = _archived_path(row)
    out_id = str(uuid.uuid4()) if new_id else session_id
    dest = paths.session_file(target_cwd, out_id)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with src.open(encoding="utf-8") as fin, dest.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                fout.write(line + "\n")
                continue
            if "cwd" in rec:
                rec["cwd"] = target_cwd
            if new_id and "sessionId" in rec:
                rec["sessionId"] = out_id
            fout.write(json.dumps(rec) + "\n")

    return {
        "session_id": out_id,
        "target_cwd": target_cwd,
        "destination": str(dest),
        "command": f"cd {target_cwd} && claude --resume {out_id}",
    }


def delete(session_id: str, purge_archive: bool = False) -> dict:
    """Remove a saved conversation from the index (and optionally its JSONL)."""
    row = store.get(session_id)
    if row is None:
        raise SaveError(f"No saved conversation with id {session_id!r}.")
    store.delete(session_id)
    purged = False
    if purge_archive:
        archive_path = Path(row["archive_path"])
        if archive_path.is_file():
            archive_path.unlink()
            purged = True
    return {"session_id": session_id, "deleted": True, "archive_purged": purged}
