"""Typer CLI for saving, resuming, and exporting Claude Code conversations."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import core

app = typer.Typer(
    add_completion=False,
    help="Save, resume, and export Claude Code conversations by session id.",
)
console = Console()
err = Console(stderr=True)


def _fail(exc: Exception) -> None:
    err.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=1)


@app.command()
def save(
    session_id: Optional[str] = typer.Option(None, "--id", help="Session id to save."),
    cwd: Optional[str] = typer.Option(
        None, "--cwd", help="Project dir to save the latest session from."
    ),
    tag: list[str] = typer.Option([], "--tag", help="Tag(s) to attach (repeatable)."),
    regenerate: bool = typer.Option(
        False,
        "--regenerate",
        help="Rewrite the summary via the Claude API (needs ANTHROPIC_API_KEY).",
    ),
) -> None:
    """Archive a conversation (defaults to the latest session in CWD)."""
    try:
        meta = core.save(session_id=session_id, cwd=cwd, tags=list(tag), regenerate=regenerate)
    except core.SaveError as exc:
        _fail(exc)
    console.print(f"[green]Saved[/green] {meta.session_id} — [bold]{meta.title}[/bold]")
    console.print(
        f"  cwd={meta.cwd or '?'}  branch={meta.git_branch or '?'}  "
        f"msgs={meta.user_count}/{meta.assistant_count}  files={len(meta.files)}"
    )


@app.command(name="list")
def list_cmd(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Text filter."),
    tag: list[str] = typer.Option([], "--tag", help="Filter by tag(s)."),
    limit: int = typer.Option(50, "--limit", help="Max rows."),
) -> None:
    """List saved conversations, newest first."""
    rows = core.list_saved(query=query, tags=list(tag), limit=limit)
    if not rows:
        console.print("[yellow]No saved conversations.[/yellow]")
        return
    table = Table(show_lines=False)
    table.add_column("Session id", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("cwd", style="dim")
    table.add_column("Msgs", justify="right")
    table.add_column("Saved", style="dim")
    for r in rows:
        table.add_row(
            r["session_id"],
            r["title"][:60],
            r["cwd"],
            f"{r['user_count']}/{r['assistant_count']}",
            r["saved_at"][:19],
        )
    console.print(table)


@app.command()
def show(session_id: str = typer.Argument(..., help="Saved session id.")) -> None:
    """Show full metadata and summary for a saved conversation."""
    try:
        r = core.show(session_id)
    except core.SaveError as exc:
        _fail(exc)
    console.print(f"[bold cyan]{r['session_id']}[/bold cyan] — [bold]{r['title']}[/bold]")
    console.print(f"cwd: {r['cwd']}")
    console.print(f"branch: {r['git_branch']}   version: {r['version']}")
    console.print(f"messages: {r['user_count']} user / {r['assistant_count']} assistant")
    console.print(f"tokens: {r['total_input_tokens']} in / {r['total_output_tokens']} out")
    console.print(f"saved: {r['saved_at']}   tags: {', '.join(r['tags']) or '-'}")
    if r["files"]:
        console.print(f"\n[bold]Files ({len(r['files'])}):[/bold]")
        for f in r["files"]:
            console.print(f"  - {f}")
    console.print(f"\n[bold]Summary:[/bold]\n{r['summary']}")


@app.command()
def restore(session_id: str = typer.Argument(..., help="Saved session id.")) -> None:
    """Place the JSONL back in its project dir so `claude --resume` works."""
    try:
        res = core.restore(session_id)
    except core.SaveError as exc:
        _fail(exc)
    status = "restored to" if res["restored"] else "already present at"
    console.print(f"[green]Session {status}[/green] {res['destination']}")
    console.print(f"Run: [bold]{res['command']}[/bold]")


@app.command()
def export(
    session_id: str = typer.Argument(..., help="Saved session id."),
    target_cwd: str = typer.Argument(..., help="Project dir to export into."),
    new_id: bool = typer.Option(False, "--new-id", help="Assign a fresh session id."),
    rewrite_paths: bool = typer.Option(
        True,
        "--rewrite-paths/--no-rewrite-paths",
        help="Re-path embedded file paths under the original cwd too (default: on).",
    ),
) -> None:
    """Copy a conversation into another project, re-pathing its cwd."""
    try:
        res = core.export(session_id, target_cwd, new_id=new_id, rewrite_paths=rewrite_paths)
    except core.SaveError as exc:
        _fail(exc)
    console.print(f"[green]Exported to[/green] {res['destination']}")
    console.print(f"Run: [bold]{res['command']}[/bold]")


@app.command()
def delete(
    session_id: Optional[str] = typer.Argument(None, help="Saved session id (omit for bulk)."),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Bulk: delete matches."),
    tag: list[str] = typer.Option([], "--tag", help="Bulk: delete sessions with tag(s)."),
    purge_archive: bool = typer.Option(False, "--purge", help="Also delete the archived JSONL."),
) -> None:
    """Remove a saved conversation, or bulk-delete by --query / --tag."""
    if session_id is None and not query and not tag:
        _fail(core.SaveError("Pass a session id, or --query / --tag for a bulk delete."))
    try:
        if session_id is not None:
            res = core.delete(session_id, purge_archive=purge_archive)
            extra = " (archive purged)" if res["archive_purged"] else ""
            console.print(f"[green]Deleted[/green] {session_id}{extra}")
        else:
            res = core.delete_where(query=query, tags=list(tag), purge_archive=purge_archive)
            console.print(f"[green]Deleted[/green] {res['count']} conversation(s)")
    except core.SaveError as exc:
        _fail(exc)


if __name__ == "__main__":
    app()
