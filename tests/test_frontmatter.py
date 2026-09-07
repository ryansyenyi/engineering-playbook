# tests/test_frontmatter.py
from datetime import date

from playbook import frontmatter

VALID = """---
title: JWT
module: authentication
status: reviewed
reviewed: 2026-09-07
review_interval: 180
tags: [Authentication, Tokens]
sources:
  - { type: rfc, name: "RFC 7519", url: "https://www.rfc-editor.org/rfc/rfc7519" }
---

# JWT

Body text.
"""


def test_parse_valid_page():
    page, problems = frontmatter.parse("modules/authentication/jwt.md", VALID)
    assert problems == []
    assert page.title == "JWT"
    assert page.module == "authentication"
    assert page.status == "reviewed"
    assert page.tags == ("Authentication", "Tokens")
    assert page.reviewed == date(2026, 9, 7)
    assert page.review_interval == 180
    assert page.sources[0].name == "RFC 7519"
    assert page.generated is False


def test_review_due_is_reviewed_plus_interval():
    page, _ = frontmatter.parse("p.md", VALID)
    assert page.review_due == date(2027, 3, 6)


def test_review_due_is_none_without_reviewed_date():
    text = "---\ntitle: T\nmodule: m\nstatus: stub\ntags: [T]\n---\n\nbody\n"
    page, problems = frontmatter.parse("p.md", text)
    assert problems == []
    assert page.review_due is None
    assert page.review_interval == frontmatter.DEFAULT_REVIEW_INTERVAL


def test_missing_front_matter_is_a_problem():
    page, problems = frontmatter.parse("p.md", "# No front matter\n")
    assert page is None
    assert problems == [frontmatter.Problem("p.md", "front-matter", "missing or malformed")]


def test_missing_required_fields_are_all_reported_together():
    page, problems = frontmatter.parse("p.md", "---\ntitle: T\n---\n\nbody\n")
    assert page is None
    fields = {problem.field for problem in problems}
    assert fields == {"module", "status", "tags"}


def test_unknown_status_is_a_problem():
    text = "---\ntitle: T\nmodule: m\nstatus: published\ntags: [T]\n---\n\nbody\n"
    _, problems = frontmatter.parse("p.md", text)
    assert [problem.field for problem in problems] == ["status"]


def test_malformed_reviewed_date_is_a_problem():
    text = "---\ntitle: T\nmodule: m\nstatus: draft\ntags: [T]\nreviewed: 'last tuesday'\n---\n\nbody\n"
    _, problems = frontmatter.parse("p.md", text)
    assert [problem.field for problem in problems] == ["reviewed"]


def test_reviewed_status_requires_a_reviewed_date():
    text = "---\ntitle: T\nmodule: m\nstatus: reviewed\ntags: [T]\n---\n\nbody\n"
    _, problems = frontmatter.parse("p.md", text)
    assert [problem.field for problem in problems] == ["reviewed"]


def test_non_positive_review_interval_is_a_problem():
    text = "---\ntitle: T\nmodule: m\nstatus: draft\ntags: [T]\nreview_interval: 0\n---\n\nbody\n"
    _, problems = frontmatter.parse("p.md", text)
    assert [problem.field for problem in problems] == ["review_interval"]


def test_malformed_source_is_a_problem():
    text = "---\ntitle: T\nmodule: m\nstatus: draft\ntags: [T]\nsources:\n  - {name: X}\n---\n\nbody\n"
    _, problems = frontmatter.parse("p.md", text)
    assert [problem.field for problem in problems] == ["sources[0]"]


def test_generated_pages_only_require_a_title():
    text = "---\ntitle: Changelog\ngenerated: true\n---\n\n# Changelog\n"
    page, problems = frontmatter.parse("changelog.md", text)
    assert problems == []
    assert page.generated is True


def test_problem_str_is_actionable():
    problem = frontmatter.Problem("modules/a/b.md", "status", "required")
    assert str(problem) == "modules/a/b.md: status: required"


def test_load_all_walks_the_tree_in_sorted_order(tmp_path):
    (tmp_path / "modules").mkdir()
    (tmp_path / "b.md").write_text(VALID, encoding="utf-8")
    (tmp_path / "modules" / "a.md").write_text(VALID, encoding="utf-8")
    pages, problems = frontmatter.load_all(tmp_path)
    assert problems == []
    assert [page.path for page in pages] == ["b.md", "modules/a.md"]
