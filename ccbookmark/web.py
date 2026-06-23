"""FastAPI web UI for the save/resume/export engine.

Serves a single static page plus a small JSON API, all backed by ``core``.
Run with::

    uv run ccbookmark-web        # http://127.0.0.1:8765
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import core

_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="ccbookmark", docs_url="/api/docs", openapi_url="/api/openapi.json")


class SaveRequest(BaseModel):
    session_id: str | None = None
    cwd: str | None = None
    tags: list[str] = []


class ExportRequest(BaseModel):
    target_cwd: str
    new_id: bool = False


def _guard(fn):
    """Translate :class:`core.SaveError` into a 404 HTTP response."""
    try:
        return fn()
    except core.SaveError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sessions")
def api_list(query: str | None = None, tag: str | None = None, limit: int = 100) -> list[dict]:
    """List saved conversations, optionally filtered by text/single tag."""
    return core.list_saved(query=query, tags=[tag] if tag else None, limit=limit)


@app.get("/api/live")
def api_live(cwd: str | None = None, limit: int = 100) -> list[dict]:
    """List live Claude Code sessions available to save."""
    return core.list_live(cwd=cwd, limit=limit)


@app.get("/api/sessions/{session_id}")
def api_show(session_id: str) -> dict:
    """Full metadata + summary for one saved conversation."""
    return _guard(lambda: core.show(session_id))


@app.post("/api/sessions/save")
def api_save(req: SaveRequest) -> dict:
    """Save a conversation (by id, or the latest in a cwd)."""
    meta = _guard(lambda: core.save(session_id=req.session_id, cwd=req.cwd, tags=req.tags))
    return core.show(meta.session_id)


@app.post("/api/sessions/{session_id}/restore")
def api_restore(session_id: str) -> dict:
    """Place the JSONL back in its project dir; returns the resume command."""
    return _guard(lambda: core.restore(session_id))


@app.post("/api/sessions/{session_id}/export")
def api_export(session_id: str, req: ExportRequest) -> dict:
    """Copy a conversation into another project, re-pathing its cwd."""
    return _guard(lambda: core.export(session_id, req.target_cwd, new_id=req.new_id))


@app.delete("/api/sessions/{session_id}")
def api_delete(session_id: str, purge: bool = False) -> dict:
    """Remove a saved conversation from the library."""
    return _guard(lambda: core.delete(session_id, purge_archive=purge))


@app.get("/")
def index() -> FileResponse:
    """Serve the single-page UI."""
    return FileResponse(_STATIC / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def main() -> None:
    """Entry point: launch the web UI with uvicorn."""
    import os

    import uvicorn

    host = os.environ.get("CCBOOKMARK_HOST", "127.0.0.1")
    port = int(os.environ.get("CCBOOKMARK_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
