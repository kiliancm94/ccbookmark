# Contributing to ccbookmark

Thanks for your interest! ccbookmark is a small, focused tool — contributions
that keep it simple and well-tested are very welcome.

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
git clone https://github.com/kiliancm94/ccbookmark.git
cd ccbookmark
uv sync --extra dev
```

## Project layout

```
ccbookmark/
  paths.py        path <-> project-dir encoding, locate session files
  parser.py       stream-parse a session JSONL -> SessionMeta
  store.py        SQLite metadata index (stdlib sqlite3)
  core.py         save / list / list_live / show / restore / export / delete
  cli.py          Typer CLI         -> calls core
  mcp_server.py   FastMCP server    -> calls core
  web.py          FastAPI + static  -> calls core
  static/         single-page web UI (no build step)
tests/            pytest + a synthetic session fixture
```

`core.py` is the single source of truth; the CLI, MCP server, and web UI are all
thin wrappers over it. New behavior should go in `core` (with tests) and then be
exposed through the interfaces as needed.

## Before opening a PR

Run the full check suite — CI runs the same on every PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Please add a test for every new feature or bug fix. Tests must not touch your
real Claude Code store or library — use `monkeypatch` to point
`CLAUDE_CONFIG_DIR` and `CCBOOKMARK_HOME` at a temp dir (see `tests/test_core.py`).

## Guidelines

- Keep changes surgical and match the existing style.
- Type all code in 3.11+ style.
- Update the README when you change user-facing behavior.

## Ideas / good first issues

- `--regenerate` flag to write a richer summary via the Claude API (optional dep).
- A TUI (e.g. Textual) as a fourth interface over `core`.
- Bulk operations (export/delete by tag or query).
- Rewrite embedded file paths on export so file context follows the move.
