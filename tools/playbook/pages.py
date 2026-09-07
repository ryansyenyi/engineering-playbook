"""Render generated markdown blocks from page metadata and git history."""

from __future__ import annotations

from datetime import date, datetime

from playbook.frontmatter import Page
from playbook.gitmeta import Commit


def _table(header: list[str], rows: list[str]) -> str:
    divider = "| " + " | ".join("---" for _ in header) + " |"
    return "\n".join(["| " + " | ".join(header) + " |", divider, *rows])


def _content_pages(all_pages: list[Page]) -> dict[str, Page]:
    return {page.path: page for page in all_pages if not page.generated}


def render_references(page: Page) -> str:
    if not page.sources:
        return "_No sources recorded yet._"
    rows = [
        f"| {source.type.upper() if len(source.type) <= 3 else source.type.title()} "
        f"| [{source.name}]({source.url}) |"
        for source in page.sources
    ]
    return _table(["Type", "Source"], rows)


def render_page_footer(page: Page) -> str:
    parts = [f"**Status:** {page.status}"]
    if page.reviewed is not None and page.review_due is not None:
        parts.append(f"**Last reviewed:** {page.reviewed.isoformat()}")
        parts.append(f"**Review due:** {page.review_due.isoformat()}")
    return " · ".join(parts)


def render_adr_index(all_pages: list[Page]) -> str:
    decisions = sorted(
        (
            page
            for page in _content_pages(all_pages).values()
            if page.path.startswith("decisions/") and page.path != "decisions/index.md"
        ),
        key=lambda page: page.path,
    )
    if not decisions:
        return "_No decision records yet._"
    rows = [
        f"| [{page.title}]({page.path[len('decisions/'):]}) | {page.module} "
        f"| {page.status} | {page.reviewed.isoformat() if page.reviewed else '—'} |"
        for page in decisions
    ]
    return _table(["Decision", "Module", "Status", "Date"], rows)


def render_recently_updated(
    all_pages: list[Page], latest: dict[str, Commit], limit: int = 10
) -> str:
    known = _content_pages(all_pages)
    dated = [
        (commit.date, path) for path, commit in latest.items() if path in known
    ]
    if not dated:
        return "_No history yet._"
    dated.sort(key=lambda item: (-item[0].toordinal(), item[1]))
    rows = [
        f"| {when.isoformat()} | [{known[path].title}]({path}) | {known[path].module} |"
        for when, path in dated[:limit]
    ]
    return _table(["Updated", "Page", "Module"], rows)


def render_changelog(commits: list[Commit], all_pages: list[Page]) -> str:
    known = _content_pages(all_pages)
    months: dict[str, list[str]] = {}
    for commit in commits:
        touched = sorted(path for path in commit.paths if path in known)
        if not touched:
            continue
        links = ", ".join(f"[{known[path].title}]({path})" for path in touched)
        month = commit.date.strftime("%Y-%m")
        months.setdefault(month, []).append(
            f"| {commit.date.isoformat()} | {links} | {commit.subject} |"
        )
    if not months:
        return "_No history yet._"
    sections = []
    for month in sorted(months, reverse=True):
        heading = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        table = _table(["Date", "Pages", "Change"], months[month])
        sections.append(f"## {heading}\n\n{table}")
    return "\n\n".join(sections)


def render_research_queue(all_pages: list[Page], today: date) -> str:
    rows = []
    for page in sorted(_content_pages(all_pages).values(), key=lambda p: p.path):
        if page.status == "stub":
            reason = "stub — not written yet"
        elif page.review_due is not None and page.review_due < today:
            reason = f"review overdue since {page.review_due.isoformat()}"
        else:
            continue
        rows.append(f"| [{page.title}]({page.path}) | {page.module} | {reason} |")
    if not rows:
        return "_Nothing queued. Every page is written and within its review interval._"
    return _table(["Page", "Module", "Reason"], rows)
