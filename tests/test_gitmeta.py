# tests/test_gitmeta.py
import subprocess
from datetime import date
from pathlib import Path

import pytest

from playbook import gitmeta


def run(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    run(tmp_path, "init", "-q", "-b", "main")
    run(tmp_path, "config", "user.email", "test@example.com")
    run(tmp_path, "config", "user.name", "Test")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "first.md").write_text("one\n", encoding="utf-8")
    run(tmp_path, "add", "-A")
    run(tmp_path, "commit", "-q", "-m", "docs: add first page")
    (docs / "second.md").write_text("two\n", encoding="utf-8")
    (tmp_path / "outside.md").write_text("ignored\n", encoding="utf-8")
    run(tmp_path, "add", "-A")
    run(tmp_path, "commit", "-q", "-m", "docs: add second page")
    return tmp_path


def test_history_returns_commits_newest_first(repo):
    commits = gitmeta.history(repo, repo / "docs")
    assert [commit.subject for commit in commits] == [
        "docs: add second page",
        "docs: add first page",
    ]


def test_history_paths_are_relative_to_docs_dir(repo):
    commits = gitmeta.history(repo, repo / "docs")
    assert commits[0].paths == ("second.md",)
    assert commits[1].paths == ("first.md",)


def test_history_excludes_files_outside_docs(repo):
    commits = gitmeta.history(repo, repo / "docs")
    assert all("outside.md" not in commit.paths for commit in commits)


def test_history_dates_are_dates(repo):
    commits = gitmeta.history(repo, repo / "docs")
    assert isinstance(commits[0].date, date)


def test_history_is_empty_outside_a_repository(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    assert gitmeta.history(tmp_path, docs) == []


def test_latest_by_path_keeps_the_newest_commit(repo):
    commits = gitmeta.history(repo, repo / "docs")
    latest = gitmeta.latest_by_path(commits)
    assert latest["second.md"].subject == "docs: add second page"
    assert latest["first.md"].subject == "docs: add first page"
