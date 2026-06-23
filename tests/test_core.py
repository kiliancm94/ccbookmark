import shutil
from pathlib import Path

import pytest

from ccbookmark import core, paths

FIXTURE = Path(__file__).parent / "fixtures" / "sample-session.jsonl"
SESSION_ID = "11111111-2222-3333-4444-555555555555"
DEMO_CWD = "/tmp/demo-proj"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Isolate both the Claude store and our library under tmp_path."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.setenv("CCBOOKMARK_HOME", str(tmp_path / "lib"))
    # Plant the fixture as a live session in the demo project's dir.
    live = paths.session_file(DEMO_CWD, SESSION_ID)
    live.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE, live)
    return tmp_path


def test_save_then_list_and_show(env):
    meta = core.save(session_id=SESSION_ID, tags=["demo"])
    assert meta.session_id == SESSION_ID
    assert (paths.archive_dir() / f"{SESSION_ID}.jsonl").is_file()

    rows = core.list_saved()
    assert len(rows) == 1
    assert rows[0]["title"] == "Build a log file parser"

    row = core.show(SESSION_ID)
    assert row["tags"] == ["demo"]
    assert row["cwd"] == DEMO_CWD


def test_save_latest_by_cwd(env):
    meta = core.save(cwd=DEMO_CWD)
    assert meta.session_id == SESSION_ID


def test_restore_writes_back_to_project_dir(env):
    core.save(session_id=SESSION_ID)
    dest = paths.session_file(DEMO_CWD, SESSION_ID)
    dest.unlink()  # simulate a deleted live session
    res = core.restore(SESSION_ID)
    assert res["restored"] is True
    assert dest.is_file()
    assert res["command"] == f"cd {DEMO_CWD} && claude --resume {SESSION_ID}"


def test_export_repaths_cwd(env):
    core.save(session_id=SESSION_ID)
    res = core.export(SESSION_ID, "/tmp/other-proj", new_id=True)
    assert res["session_id"] != SESSION_ID
    dest = Path(res["destination"])
    assert dest.is_file()
    assert "-tmp-other-proj" in str(dest.parent)
    # Every record's top-level cwd is re-pathed; embedded file paths are not.
    import json

    for line in dest.read_text().splitlines():
        rec = json.loads(line)
        if "cwd" in rec:
            assert rec["cwd"] == "/tmp/other-proj"
        if "sessionId" in rec:
            assert rec["sessionId"] == res["session_id"]


def test_delete(env):
    core.save(session_id=SESSION_ID)
    res = core.delete(SESSION_ID, purge_archive=True)
    assert res["deleted"] is True
    assert res["archive_purged"] is True
    assert core.list_saved() == []


def test_save_missing_session_raises(env):
    with pytest.raises(core.SaveError):
        core.save(session_id="does-not-exist")
