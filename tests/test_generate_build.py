import subprocess
from datetime import date
from pathlib import Path

import pytest

import generate

PAGE = """---
title: JWT
module: authentication
status: stub
tags: [Authentication]
---

# JWT
"""


def run(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    run(tmp_path, "init", "-q", "-b", "main")
    run(tmp_path, "config", "user.email", "test@example.com")
    run(tmp_path, "config", "user.name", "Test")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "jwt.md").write_text(PAGE, encoding="utf-8")
    run(tmp_path, "add", "-A")
    run(tmp_path, "commit", "-q", "-m", "docs: add jwt")
    return tmp_path


def test_build_writes_three_generated_pages(repo):
    outputs, problems = generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))
    assert problems == []
    assert set(outputs) == {
        repo / "docs" / "recently-updated.md",
        repo / "docs" / "changelog.md",
        repo / "docs" / "research-queue.md",
    }


def test_generated_pages_carry_generated_front_matter(repo):
    outputs, _ = generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))
    text = outputs[repo / "docs" / "changelog.md"]
    assert text.startswith("---\ntitle: Changelog\ngenerated: true\n---\n")


def test_build_includes_git_derived_content(repo):
    outputs, _ = generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))
    assert "docs: add jwt" in outputs[repo / "docs" / "changelog.md"]
    assert "[JWT](jwt.md)" in outputs[repo / "docs" / "recently-updated.md"]


def test_build_queues_stub_pages(repo):
    outputs, _ = generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))
    assert "[JWT](jwt.md)" in outputs[repo / "docs" / "research-queue.md"]


def test_build_output_reparses_cleanly(repo):
    generate.write(generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))[0])
    outputs, problems = generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))
    assert problems == []


def test_build_is_idempotent(repo):
    generate.write(generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))[0])
    first = (repo / "docs" / "changelog.md").read_text(encoding="utf-8")
    generate.write(generate.build_outputs(repo, repo / "docs", date(2026, 9, 7))[0])
    assert (repo / "docs" / "changelog.md").read_text(encoding="utf-8") == first


def test_build_works_without_git_history(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "jwt.md").write_text(PAGE, encoding="utf-8")
    outputs, problems = generate.build_outputs(tmp_path, docs, date(2026, 9, 7))
    assert problems == []
    assert "_No history yet._" in outputs[docs / "changelog.md"]
