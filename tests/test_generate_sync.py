from pathlib import Path

import pytest

import generate

PAGE = """---
title: JWT
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication]
sources:
  - { type: rfc, name: "RFC 7519", url: "https://example.test/7519" }
---

# JWT

Body.
"""


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    (docs_dir / "modules" / "authentication").mkdir(parents=True)
    (docs_dir / "modules" / "authentication" / "jwt.md").write_text(PAGE, encoding="utf-8")
    return docs_dir


def test_sync_appends_reference_and_footer_blocks(docs):
    outputs, problems = generate.sync_outputs(docs.parent, docs)
    assert problems == []
    text = outputs[docs / "modules" / "authentication" / "jwt.md"]
    assert "<!-- generated:references start -->" in text
    assert "[RFC 7519](https://example.test/7519)" in text
    assert "**Review due:** 2027-03-06" in text


def test_sync_reports_problems_and_produces_nothing(docs):
    (docs / "broken.md").write_text("# no front matter\n", encoding="utf-8")
    outputs, problems = generate.sync_outputs(docs.parent, docs)
    assert outputs == {}
    assert [str(problem) for problem in problems] == [
        "broken.md: front-matter: missing or malformed"
    ]


def test_sync_is_idempotent(docs):
    generate.write(generate.sync_outputs(docs.parent, docs)[0])
    first = (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8")
    generate.write(generate.sync_outputs(docs.parent, docs)[0])
    second = (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8")
    assert first == second


def test_stale_is_empty_after_a_write(docs):
    outputs, _ = generate.sync_outputs(docs.parent, docs)
    generate.write(outputs)
    assert generate.stale(generate.sync_outputs(docs.parent, docs)[0]) == []


def test_main_sync_writes_and_returns_zero(docs, capsys):
    assert generate.main(["sync", "--root", str(docs.parent)]) == 0
    assert "generated:references" in (
        docs / "modules" / "authentication" / "jwt.md"
    ).read_text(encoding="utf-8")


def test_main_check_fails_on_stale_content(docs, capsys):
    assert generate.main(["sync", "--check", "--root", str(docs.parent)]) == 1
    assert "stale:" in capsys.readouterr().err


def test_main_check_passes_after_sync(docs):
    generate.main(["sync", "--root", str(docs.parent)])
    assert generate.main(["sync", "--check", "--root", str(docs.parent)]) == 0


def test_main_check_writes_nothing(docs):
    before = (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8")
    generate.main(["sync", "--check", "--root", str(docs.parent)])
    assert (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8") == before


def test_main_reports_validation_problems_and_returns_one(docs, capsys):
    (docs / "broken.md").write_text("# no front matter\n", encoding="utf-8")
    assert generate.main(["sync", "--root", str(docs.parent)]) == 1
    assert "broken.md: front-matter" in capsys.readouterr().err


def test_files_are_written_with_unix_newlines(docs):
    generate.main(["sync", "--root", str(docs.parent)])
    raw = (docs / "modules" / "authentication" / "jwt.md").read_bytes()
    assert b"\r\n" not in raw


MATRIX_PAGE = """---
title: Password hashing
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Decision matrix, Authentication]
sources: []
---

# Password hashing

<!-- generated:matrix start -->
_Matrix data is generated from data/decisions/password-hashing.csv._
<!-- generated:matrix end -->

## Why
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    (docs_dir / "matrices").mkdir(parents=True)
    (docs_dir / "matrices" / "password-hashing.md").write_text(
        MATRIX_PAGE, encoding="utf-8"
    )
    return tmp_path


def test_sync_fills_matrix_block_from_matching_csv(project):
    data_dir = project / "data" / "decisions"
    data_dir.mkdir(parents=True)
    (data_dir / "password-hashing.csv").write_text(
        "Option,Score\nArgon2id,5\nbcrypt,3\n", encoding="utf-8"
    )
    outputs, problems = generate.sync_outputs(project, project / "docs")
    assert problems == []
    text = outputs[project / "docs" / "matrices" / "password-hashing.md"]
    assert "<!-- generated:matrix start -->" in text
    assert "| Argon2id | 5 |" in text
    assert "| bcrypt | 3 |" in text


def test_sync_reports_problem_for_missing_matrix_csv(project):
    outputs, problems = generate.sync_outputs(project, project / "docs")
    assert outputs == {}
    assert len(problems) == 1
    problem = problems[0]
    assert problem.path == "matrices/password-hashing.md"
    assert "data/decisions/password-hashing.csv" in str(problem)
