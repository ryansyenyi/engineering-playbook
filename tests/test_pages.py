from datetime import date

from playbook import pages
from playbook.frontmatter import Page, Source
from playbook.gitmeta import Commit


def make_page(path, title="T", module="authentication", status="draft",
              reviewed=None, interval=180, sources=(), generated=False):
    return Page(
        path=path,
        title=title,
        module=module,
        status=status,
        tags=("Authentication",),
        sources=sources,
        reviewed=reviewed,
        review_interval=interval,
        version=None,
        generated=generated,
    )


def test_render_references_builds_a_table():
    page = make_page(
        "modules/authentication/jwt.md",
        sources=(Source("rfc", "RFC 7519", "https://example.test/7519"),),
    )
    assert pages.render_references(page) == (
        "| Type | Source |\n"
        "| --- | --- |\n"
        "| RFC | [RFC 7519](https://example.test/7519) |"
    )


def test_render_references_handles_no_sources():
    assert pages.render_references(make_page("a.md")) == "_No sources recorded yet._"


def test_render_references_escapes_a_pipe_in_the_source_name():
    page = make_page(
        "a.md",
        sources=(Source("rfc", "RFC 7519 | JWT", "https://example.test/7519"),),
    )
    assert pages.render_references(page) == (
        "| Type | Source |\n"
        "| --- | --- |\n"
        "| RFC | [RFC 7519 \\| JWT](https://example.test/7519) |"
    )


def test_render_references_labels_a_mapped_acronym_type():
    page = make_page(
        "a.md",
        sources=(Source("nist", "SP 800-63B", "https://example.test/800-63b"),),
    )
    assert "| NIST |" in pages.render_references(page)


def test_render_references_title_cases_an_unmapped_type():
    page = make_page(
        "a.md",
        sources=(Source("blog", "Some Post", "https://example.test/post"),),
    )
    assert "| Blog |" in pages.render_references(page)


def test_render_page_footer_without_review_date():
    assert pages.render_page_footer(make_page("a.md")) == "**Status:** draft"


def test_render_page_footer_with_review_date():
    page = make_page("a.md", status="reviewed", reviewed=date(2026, 9, 7))
    assert pages.render_page_footer(page) == (
        "**Status:** reviewed · **Last reviewed:** 2026-09-07 · **Review due:** 2027-03-06"
    )


def test_render_adr_index_lists_decisions_only():
    all_pages = [
        make_page("decisions/index.md", title="Decisions"),
        make_page("decisions/0001-argon2id.md", title="Use Argon2id",
                  status="reviewed", reviewed=date(2026, 9, 7)),
        make_page("modules/authentication/jwt.md", title="JWT"),
    ]
    result = pages.render_adr_index(all_pages)
    assert "[Use Argon2id](0001-argon2id.md)" in result
    assert "JWT" not in result
    assert "Decisions" not in result


def test_render_adr_index_handles_no_decisions():
    assert pages.render_adr_index([]) == "_No decision records yet._"


def test_render_recently_updated_is_newest_first():
    all_pages = [make_page("a.md", title="A"), make_page("b.md", title="B")]
    latest = {
        "a.md": Commit("s1", date(2026, 9, 1), "old", ("a.md",)),
        "b.md": Commit("s2", date(2026, 9, 5), "new", ("b.md",)),
    }
    result = pages.render_recently_updated(all_pages, latest)
    assert result.index("[B](b.md)") < result.index("[A](a.md)")


def test_render_recently_updated_breaks_date_ties_by_path():
    all_pages = [make_page("b.md", title="B"), make_page("a.md", title="A")]
    same = date(2026, 9, 1)
    latest = {
        "b.md": Commit("s1", same, "x", ("b.md",)),
        "a.md": Commit("s2", same, "x", ("a.md",)),
    }
    result = pages.render_recently_updated(all_pages, latest)
    assert result.index("[A](a.md)") < result.index("[B](b.md)")


def test_render_recently_updated_respects_the_limit():
    all_pages = [make_page(f"p{i}.md", title=f"P{i}") for i in range(5)]
    latest = {
        f"p{i}.md": Commit(f"s{i}", date(2026, 9, i + 1), "x", (f"p{i}.md",))
        for i in range(5)
    }
    result = pages.render_recently_updated(all_pages, latest, limit=2)
    assert result.count("| 2026-") == 2


def test_render_recently_updated_handles_no_history():
    assert pages.render_recently_updated([make_page("a.md")], {}) == "_No history yet._"


def test_render_changelog_groups_by_month_newest_first():
    all_pages = [make_page("a.md", title="A"), make_page("b.md", title="B")]
    commits = [
        Commit("s2", date(2026, 10, 2), "docs: update B", ("b.md",)),
        Commit("s1", date(2026, 9, 1), "docs: add A", ("a.md",)),
    ]
    result = pages.render_changelog(commits, all_pages)
    assert result.index("## October 2026") < result.index("## September 2026")
    assert "docs: update B" in result


def test_render_changelog_ignores_commits_touching_no_known_page():
    all_pages = [make_page("a.md", title="A")]
    commits = [Commit("s1", date(2026, 9, 1), "chore: config", ("gone.md",))]
    assert pages.render_changelog(commits, all_pages) == "_No history yet._"


def test_render_research_queue_lists_stubs_and_overdue_pages():
    all_pages = [
        make_page("stub.md", title="Stub", status="stub"),
        make_page("overdue.md", title="Overdue", status="reviewed",
                  reviewed=date(2025, 1, 1)),
        make_page("fresh.md", title="Fresh", status="reviewed",
                  reviewed=date(2026, 9, 1)),
    ]
    result = pages.render_research_queue(all_pages, date(2026, 9, 7))
    assert "[Stub](stub.md)" in result
    assert "[Overdue](overdue.md)" in result
    assert "Fresh" not in result


def test_render_research_queue_skips_generated_pages():
    all_pages = [make_page("changelog.md", title="Changelog", status="stub", generated=True)]
    assert pages.render_research_queue(all_pages, date(2026, 9, 7)) == (
        "_Nothing queued. Every page is written and within its review interval._"
    )


def test_render_matrix_builds_a_table_from_csv_rows():
    rows = [
        ["Option", "Score", "Verdict"],
        ["Argon2id", "5", "Default choice"],
        ["bcrypt", "3", "Acceptable legacy"],
    ]
    assert pages.render_matrix(rows) == (
        "| Option | Score | Verdict |\n"
        "| --- | --- | --- |\n"
        "| Argon2id | 5 | Default choice |\n"
        "| bcrypt | 3 | Acceptable legacy |"
    )


def test_render_matrix_handles_empty_input():
    assert pages.render_matrix([]) == "_No matrix data._"


def test_render_matrix_escapes_a_pipe_in_a_cell():
    rows = [
        ["Option", "Verdict"],
        ["Argon2id", "Default | recommended"],
    ]
    assert pages.render_matrix(rows) == (
        "| Option | Verdict |\n"
        "| --- | --- |\n"
        "| Argon2id | Default \\| recommended |"
    )
