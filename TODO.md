# TODO

## Submit to awesome-claude-code (~1 week)

⚠️ **Do NOT open a PR or use the `gh` CLI** — the repo's rules require the web
issue form and warn of bans for bypassing it. Submission must be made by a human.

**Form:** https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml

Paste these values:

| Field | Value |
|-------|-------|
| Display Name | `ccbookmark` |
| Category | `Tooling` |
| Primary Link | `https://github.com/kiliancm94/ccbookmark` |
| Author Name | `Kilian Cañizares Mata` |
| Author Link | `https://github.com/kiliancm94` |
| License | `MIT` |

**Description:**

> Bookmark, resume, and export Claude Code conversations. Reads the local session
> JSONL under `~/.claude/projects`, archives selected conversations into a
> SQLite-indexed library with extracted summaries, and can resume one by id or
> **export it into a different project** (re-pathing `cwd` and embedded file paths)
> so `claude --resume` works there — something native resume can't do. Three
> interfaces over one engine: a CLI, an MCP server, and a single-page FastAPI web
> UI. Fully local — no network calls, no telemetry, no bypass-permissions.
> Validate: `git clone https://github.com/kiliancm94/ccbookmark && cd ccbookmark &&
> uv sync && uv run ccbookmark save --cwd <any Claude Code project dir> && uv run
> ccbookmark list`.

After it's approved, add the badge to the README:

```markdown
[![Mentioned in Awesome Claude Code](https://awesome.re/mentioned-badge.svg)](https://github.com/hesreallyhim/awesome-claude-code)
```

## Publish to PyPI (so `uvx ccbookmark` works)

The release workflow (`.github/workflows/publish.yml`) and the GitHub `pypi`
environment are already in place. Two human steps remain:

1. **Configure a PyPI Trusted Publisher** at
   https://pypi.org/manage/account/publishing/ — "Add a pending publisher":
   - PyPI Project Name: `ccbookmark`
   - Owner: `kiliancm94`
   - Repository name: `ccbookmark`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
2. **Push a version tag** to trigger the workflow:
   ```bash
   git tag v0.2.0 && git push origin v0.2.0
   ```

The workflow builds the sdist+wheel and publishes via OIDC (no API token).
