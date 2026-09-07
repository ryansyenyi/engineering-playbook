"""Parse and validate playbook page front-matter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

STATUSES = ("stub", "draft", "reviewed")
DEFAULT_REVIEW_INTERVAL = 180


@dataclass(frozen=True)
class Source:
    type: str
    name: str
    url: str


@dataclass(frozen=True)
class Problem:
    path: str
    field: str
    problem: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.problem}"


@dataclass(frozen=True)
class Page:
    path: str
    title: str
    module: str
    status: str
    tags: tuple[str, ...]
    sources: tuple[Source, ...]
    reviewed: date | None
    review_interval: int
    version: str | None
    generated: bool

    @property
    def review_due(self) -> date | None:
        if self.reviewed is None:
            return None
        return self.reviewed + timedelta(days=self.review_interval)


def split_front_matter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def parse(path: str, text: str) -> tuple[Page | None, list[Problem]]:
    raw, _body = split_front_matter(text)
    if raw is None:
        return None, [Problem(path, "front-matter", "missing or malformed")]
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as error:
        return None, [Problem(path, "front-matter", f"invalid YAML: {error}")]
    if not isinstance(data, dict):
        return None, [Problem(path, "front-matter", "must be a mapping")]

    problems: list[Problem] = []
    generated = data.get("generated") is True

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        problems.append(Problem(path, "title", "required, must be a non-empty string"))

    module = data.get("module")
    if not generated and (not isinstance(module, str) or not module.strip()):
        problems.append(Problem(path, "module", "required, must be a non-empty string"))

    status = data.get("status")
    if not generated and status not in STATUSES:
        problems.append(
            Problem(path, "status", f"required, one of: {', '.join(STATUSES)}")
        )

    raw_tags = data.get("tags") or []
    tags: tuple[str, ...] = ()
    if not isinstance(raw_tags, list) or not all(isinstance(t, str) for t in raw_tags):
        problems.append(Problem(path, "tags", "must be a list of strings"))
    elif not generated and not raw_tags:
        problems.append(Problem(path, "tags", "required, at least one tag"))
    else:
        tags = tuple(raw_tags)

    reviewed: date | None = None
    raw_reviewed = data.get("reviewed")
    if isinstance(raw_reviewed, date):
        reviewed = raw_reviewed
    elif isinstance(raw_reviewed, str):
        try:
            reviewed = date.fromisoformat(raw_reviewed)
        except ValueError:
            problems.append(Problem(path, "reviewed", "must be an ISO date (YYYY-MM-DD)"))
    elif raw_reviewed is not None:
        problems.append(Problem(path, "reviewed", "must be an ISO date (YYYY-MM-DD)"))
    if status == "reviewed" and reviewed is None and raw_reviewed is None:
        problems.append(Problem(path, "reviewed", "required when status is 'reviewed'"))

    interval = data.get("review_interval", DEFAULT_REVIEW_INTERVAL)
    if isinstance(interval, bool) or not isinstance(interval, int) or interval <= 0:
        problems.append(Problem(path, "review_interval", "must be a positive integer"))
        interval = DEFAULT_REVIEW_INTERVAL

    sources: list[Source] = []
    for index, item in enumerate(data.get("sources") or []):
        if not isinstance(item, dict) or not {"type", "name", "url"} <= set(item):
            problems.append(
                Problem(
                    path,
                    f"sources[{index}]",
                    "must be a mapping with type, name and url",
                )
            )
            continue
        sources.append(Source(str(item["type"]), str(item["name"]), str(item["url"])))

    if problems:
        return None, problems

    return (
        Page(
            path=path,
            title=str(title),
            module=str(module) if isinstance(module, str) else "",
            status=str(status) if isinstance(status, str) else "",
            tags=tags,
            sources=tuple(sources),
            reviewed=reviewed,
            review_interval=interval,
            version=str(data["version"]) if "version" in data else None,
            generated=generated,
        ),
        [],
    )


def load_all(docs_dir: Path) -> tuple[list[Page], list[Problem]]:
    pages: list[Page] = []
    problems: list[Problem] = []
    for file in sorted(docs_dir.rglob("*.md")):
        relative = file.relative_to(docs_dir).as_posix()
        page, found = parse(relative, file.read_text(encoding="utf-8"))
        problems.extend(found)
        if page is not None:
            pages.append(page)
    return pages, problems
