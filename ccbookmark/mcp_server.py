"""MCP server exposing the save/resume/export engine to Claude Code.

Register with (run from a clone of this repo)::

    claude mcp add --scope user ccbookmark -- \
        uv run --directory "$(pwd)" ccbookmark-mcp

Then from inside Claude Code you can ask to "bookmark this conversation", "list
my bookmarked conversations", or "prepare session <id> for resume".
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP("ccbookmark")


@mcp.tool()
def save_conversation(
    session_id: str | None = None,
    cwd: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Save a Claude Code conversation to the library.

    Without ``session_id`` the most recently modified session in ``cwd`` (or the
    server's working directory) is saved. An MCP server cannot reliably know the
    *current* session id, so pass one explicitly to be certain.
    """
    meta = core.save(session_id=session_id, cwd=cwd, tags=tags or [])
    return {
        "session_id": meta.session_id,
        "title": meta.title,
        "cwd": meta.cwd,
        "git_branch": meta.git_branch,
        "user_count": meta.user_count,
        "assistant_count": meta.assistant_count,
        "files": meta.files,
        "summary": meta.summary,
    }


@mcp.tool()
def list_saved(
    query: str | None = None, tags: list[str] | None = None, limit: int = 50
) -> list[dict]:
    """List saved conversations (newest first), optionally filtered."""
    return core.list_saved(query=query, tags=tags or None, limit=limit)


@mcp.tool()
def show_conversation(session_id: str) -> dict:
    """Return full metadata and summary for one saved conversation."""
    return core.show(session_id)


@mcp.tool()
def restore_conversation(session_id: str) -> dict:
    """Place the saved JSONL back in its project dir and return the resume command."""
    return core.restore(session_id)


@mcp.tool()
def export_conversation(session_id: str, target_cwd: str, new_id: bool = False) -> dict:
    """Copy a saved conversation into another project, re-pathing its cwd."""
    return core.export(session_id, target_cwd, new_id=new_id)


@mcp.tool()
def delete_saved(session_id: str, purge_archive: bool = False) -> dict:
    """Remove a saved conversation from the library."""
    return core.delete(session_id, purge_archive=purge_archive)


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
