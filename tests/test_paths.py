from ccbookmark import paths


def test_encode_project_dir_replaces_slash_and_dot():
    assert paths.encode_project_dir("/Users/me/vf") == "-Users-me-vf"
    assert paths.encode_project_dir("/repo/.worktrees/x") == "-repo--worktrees-x"


def test_session_file_path(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    p = paths.session_file("/Users/me/vf", "abc")
    assert p == tmp_path / "projects" / "-Users-me-vf" / "abc.jsonl"


def test_find_latest_session(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    pdir = paths.project_dir("/Users/me/vf")
    pdir.mkdir(parents=True)
    older = pdir / "old.jsonl"
    newer = pdir / "new.jsonl"
    older.write_text("{}\n")
    newer.write_text("{}\n")
    import os

    os.utime(older, (1, 1))
    os.utime(newer, (10, 10))
    assert paths.find_latest_session("/Users/me/vf") == newer


def test_find_session_anywhere(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    pdir = paths.project_dir("/Users/me/vf")
    pdir.mkdir(parents=True)
    target = pdir / "abc.jsonl"
    target.write_text("{}\n")
    assert paths.find_session_anywhere("abc") == target
    assert paths.find_session_anywhere("missing") is None
