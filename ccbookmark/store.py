"""SQLite metadata index for saved conversations (stdlib ``sqlite3``)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from . import paths
from .parser import SessionMeta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '',
    slug                TEXT NOT NULL DEFAULT '',
    summary             TEXT NOT NULL DEFAULT '',
    first_prompt        TEXT NOT NULL DEFAULT '',
    cwd                 TEXT NOT NULL DEFAULT '',
    git_branch          TEXT NOT NULL DEFAULT '',
    project_dir         TEXT NOT NULL DEFAULT '',
    version             TEXT NOT NULL DEFAULT '',
    user_count          INTEGER NOT NULL DEFAULT 0,
    assistant_count     INTEGER NOT NULL DEFAULT 0,
    total_input_tokens  INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    first_ts            TEXT NOT NULL DEFAULT '',
    last_ts             TEXT NOT NULL DEFAULT '',
    files               TEXT NOT NULL DEFAULT '[]',
    tags                TEXT NOT NULL DEFAULT '[]',
    saved_at            TEXT NOT NULL DEFAULT '',
    archive_path        TEXT NOT NULL DEFAULT ''
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    paths.library_home().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(paths.index_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["files"] = json.loads(data.get("files") or "[]")
    data["tags"] = json.loads(data.get("tags") or "[]")
    return data


def upsert(
    meta: SessionMeta, *, project_dir: str, archive_path: str, tags: list[str], saved_at: str
) -> None:
    """Insert or replace the index row for ``meta``."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions (
                session_id, title, slug, summary, first_prompt, cwd, git_branch,
                project_dir, version, user_count, assistant_count,
                total_input_tokens, total_output_tokens, first_ts, last_ts,
                files, tags, saved_at, archive_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                meta.session_id,
                meta.title,
                meta.slug,
                meta.summary,
                meta.first_prompt,
                meta.cwd,
                meta.git_branch,
                project_dir,
                meta.version,
                meta.user_count,
                meta.assistant_count,
                meta.total_input_tokens,
                meta.total_output_tokens,
                meta.first_ts,
                meta.last_ts,
                json.dumps(meta.files),
                json.dumps(tags),
                saved_at,
                archive_path,
            ),
        )


def get(session_id: str) -> dict | None:
    """Return one saved session row as a dict, or ``None``."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    return _row_to_dict(row) if row else None


def search(query: str | None = None, tags: list[str] | None = None, limit: int = 50) -> list[dict]:
    """List saved sessions, newest first, optionally filtered by text/tags."""
    sql = "SELECT * FROM sessions"
    clauses: list[str] = []
    params: list[object] = []
    if query:
        clauses.append("(title LIKE ? OR summary LIKE ? OR first_prompt LIKE ?)")
        like = f"%{query}%"
        params += [like, like, like]
    if tags:
        for tag in tags:
            clauses.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY saved_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete(session_id: str) -> bool:
    """Remove a saved session row. Returns ``True`` if a row was deleted."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return cur.rowcount > 0
