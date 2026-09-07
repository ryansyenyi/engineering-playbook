# Engineering Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a living software architecture playbook as a Zensical static site, deployed to GitHub Pages, with a generator that derives references, page status footers, an ADR index, a changelog, a recently-updated list, and a research queue from page front-matter and git history.

**Architecture:** Content is plain Markdown with structured front-matter under `docs/`. A Python package `tools/playbook/` provides four single-responsibility units (sentinel blocks, front-matter parsing, git history, renderers), driven by a `tools/generate.py` CLI with two subcommands: `sync` writes front-matter-derived blocks into committed sources and can verify them with `--check`; `build` writes git-derived pages that are gitignored build artifacts. Curated decision matrices live as CSV under `data/decisions/` and render through the `table-reader` plugin.

**Tech Stack:** Zensical 0.0.59 (pinned), Python 3.12, uv, pytest, PyYAML, Mermaid via `pymdownx.superfences`, GitHub Actions + GitHub Pages.

**Spec:** `spec/2026-09-07-engineering-playbook-design.md`

## Global Constraints

- **Zensical is pinned exactly to `0.0.59`.** It is alpha software (0.0.x, pre-beta). Never float the version. `tags` requires >= 0.0.58 and `table-reader` requires >= 0.0.41; both are load-bearing.
- **Python >= 3.10** is Zensical's floor; this project targets **3.12**.
- **`docs/` is the published site root.** Never place specs, plans, notes, or scratch files under `docs/`. Specs live in `spec/`, plans in `spec/plans/`.
- **All generated file writes use `newline="\n"` explicitly.** Development is on Windows; without this, files churn between LF and CRLF and `--check` reports false staleness.
- **The generator must be idempotent.** Running it twice produces byte-identical files. This is tested explicitly and is what makes `--check` trustworthy.
- **Committed generated content depends only on front-matter.** Anything depending on git history or on today's date is a build-time artifact and is gitignored. Violating this makes CI fail on every commit.
- **Maximum content depth is three levels** (`modules/authentication/jwt.md`).
- **Security content has exactly one home:** `docs/security/`. `docs/modules/` links to it and never duplicates it.
- Page `status` is one of exactly `stub`, `draft`, `reviewed`.
- Default `review_interval` is `180` days.
- Replace `<user>` in every URL with the actual GitHub username before Task 10.

---

### Task 1: Project scaffold and Zensical smoke build

Establishes the toolchain and — critically — verifies which theme features Zensical actually accepts. Five of the ten features in the spec come from the Material for MkDocs surface that Zensical claims to support wholesale but does not enumerate. This task finds out.

**Files:**
- Create: `pyproject.toml`
- Create: `zensical.toml`
- Create: `docs/index.md`
- Modify: `.gitignore`

- [ ] **Step 1: Initialize the uv project and pin dependencies**

```bash
uv init --bare
uv add --dev "zensical==0.0.59" "pytest>=8,<9" "pyyaml>=6.0.2"
```

If `uv` is not installed: `winget install --id=astral-sh.uv -e` on Windows, or `pip install uv`.

- [ ] **Step 2: Set the Python floor and pytest path in `pyproject.toml`**

Add these sections (keep whatever `uv init` generated above them):

```toml
[project]
name = "engineering-playbook"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
pythonpath = ["tools"]
testpaths = ["tests"]
```

`pythonpath = ["tools"]` is what lets tests `import playbook` without an install step.

- [ ] **Step 3: Write `zensical.toml` with the full feature list**

```toml
[project]
site_name        = "Engineering Playbook"
site_description = "Living architecture playbook: patterns, standards, decisions, checklists."
docs_dir         = "docs"
site_dir         = "site"

[project.theme]
variant = "modern"
features = [
  "navigation.instant",
  "navigation.instant.prefetch",
  "navigation.instant.progress",
  "navigation.sections",
  "navigation.top",
  "toc.follow",
  "search.highlight",
  "search.suggest",
  "content.code.copy",
  "content.action.edit",
]

[[project.theme.palette]]
media = "(prefers-color-scheme: light)"
scheme = "default"
toggle = { icon = "lucide/sun", name = "Switch to dark mode" }

[[project.theme.palette]]
media = "(prefers-color-scheme: dark)"
scheme = "slate"
toggle = { icon = "lucide/moon", name = "Switch to light mode" }

[project.plugins.search]
[project.plugins.tags]
[project.plugins.table-reader]
[project.plugins.section-index]

[project.validation]
invalid_links = true
invalid_link_anchors = true

[project.markdown_extensions]
attr_list = {}
md_in_html = {}
pymdownx.superfences.custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
]
```

`attr_list` and `md_in_html` are required by card grids. The mermaid custom fence is required by every architecture diagram in the playbook.

- [ ] **Step 4: Write a throwaway `docs/index.md` that exercises the risky features**

```markdown
---
title: Engineering Playbook
---

# Engineering Playbook

Smoke test page.

<div class="grid cards" markdown>

-   __Modules__

    ---

    Architecture library.

</div>

``` mermaid
sequenceDiagram
  Client->>Server: POST /login
  Server-->>Client: 200 + Set-Cookie
```
```

- [ ] **Step 5: Build and record which features are rejected**

Run: `uv run zensical build --clean`
Expected: exit 0. Read all warnings.

If any theme feature is rejected or warned about, **delete it from `features`** — do not work around it. Record the removed features in a comment at the top of `zensical.toml`. Then re-run until the build is clean.

- [ ] **Step 6: Preview and confirm visually**

Run: `uv run zensical serve`
Open the printed URL. Confirm: the card grid renders as a card, the mermaid sequence diagram renders as a diagram (not a code block), and the light/dark toggle appears in the header.

If mermaid renders as a code block, the custom fence is misconfigured — fix before proceeding, because every module page depends on it.

- [ ] **Step 7: Extend `.gitignore`**

```
site/
.venv/
__pycache__/
*.pyc
.cache/
.pytest_cache/

# Build-time generated pages (see spec: git-derived content is never committed)
docs/recently-updated.md
docs/changelog.md
docs/research-queue.md
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock zensical.toml docs/index.md .gitignore
git commit -m "feat: scaffold zensical project with verified theme features"
```

---

### Task 2: Sentinel block replacement

The smallest, purest unit: finding and replacing `<!-- generated:name start -->` … `<!-- generated:name end -->` regions in text. Everything the generator writes goes through here.

**Files:**
- Create: `tools/playbook/__init__.py` (empty)
- Create: `tools/playbook/blocks.py`
- Test: `tests/test_blocks.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `blocks.has_block(text: str, name: str) -> bool`, `blocks.render_block(name: str, body: str) -> str`, `blocks.replace_block(text: str, name: str, body: str) -> str`, `blocks.upsert_block(text: str, name: str, body: str) -> str`, `blocks.BlockNotFound(Exception)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_blocks.py
import pytest

from playbook import blocks

PAGE = """# Title

Intro paragraph.

<!-- generated:references start -->
old body
<!-- generated:references end -->

Trailing text.
"""


def test_has_block_finds_existing_block():
    assert blocks.has_block(PAGE, "references") is True


def test_has_block_is_false_for_absent_block():
    assert blocks.has_block(PAGE, "page-footer") is False


def test_replace_block_swaps_only_the_body():
    result = blocks.replace_block(PAGE, "references", "new body")
    assert "new body" in result
    assert "old body" not in result
    assert "Intro paragraph." in result
    assert "Trailing text." in result


def test_replace_block_raises_when_absent():
    with pytest.raises(blocks.BlockNotFound):
        blocks.replace_block(PAGE, "page-footer", "body")


def test_replace_block_is_idempotent():
    once = blocks.replace_block(PAGE, "references", "new body")
    twice = blocks.replace_block(once, "references", "new body")
    assert once == twice


def test_replace_block_preserves_regex_special_characters_in_body():
    body = r"| Type | Source |\n| --- | --- |\n| RFC | [RFC 9106](https://a.example/\g<1>) |"
    result = blocks.replace_block(PAGE, "references", body)
    assert body in result


def test_upsert_block_appends_when_absent():
    result = blocks.upsert_block(PAGE, "page-footer", "**Status:** draft")
    assert result.startswith(PAGE.rstrip("\n"))
    assert result.endswith(
        "<!-- generated:page-footer start -->\n**Status:** draft\n<!-- generated:page-footer end -->\n"
    )


def test_upsert_block_replaces_when_present():
    result = blocks.upsert_block(PAGE, "references", "new body")
    assert result.count("<!-- generated:references start -->") == 1
    assert "new body" in result


def test_upsert_block_is_idempotent_across_runs():
    once = blocks.upsert_block(PAGE, "page-footer", "**Status:** draft")
    twice = blocks.upsert_block(once, "page-footer", "**Status:** draft")
    assert once == twice
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_blocks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'playbook'`

- [ ] **Step 3: Write the implementation**

```python
# tools/playbook/blocks.py
"""Sentinel-delimited generated blocks inside markdown files."""

from __future__ import annotations

import re


class BlockNotFound(Exception):
    """Raised when a requested generated block is absent from the text."""


def start_marker(name: str) -> str:
    return f"<!-- generated:{name} start -->"


def end_marker(name: str) -> str:
    return f"<!-- generated:{name} end -->"


def _pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        re.escape(start_marker(name)) + r".*?" + re.escape(end_marker(name)),
        re.DOTALL,
    )


def has_block(text: str, name: str) -> bool:
    return _pattern(name).search(text) is not None


def render_block(name: str, body: str) -> str:
    return f"{start_marker(name)}\n{body.strip()}\n{end_marker(name)}"


def replace_block(text: str, name: str, body: str) -> str:
    if not has_block(text, name):
        raise BlockNotFound(name)
    rendered = render_block(name, body)
    return _pattern(name).sub(lambda _match: rendered, text, count=1)


def upsert_block(text: str, name: str, body: str) -> str:
    if has_block(text, name):
        return replace_block(text, name, body)
    return f"{text.rstrip(chr(10))}\n\n{render_block(name, body)}\n"
```

The `sub` call passes a **function** rather than a replacement string. A string replacement would interpret `\g`, `\1`, and backslashes inside markdown tables and URLs as regex group references and corrupt the output.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_blocks.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add tools/playbook/__init__.py tools/playbook/blocks.py tests/test_blocks.py
git commit -m "feat: add sentinel block replacement"
```

---

### Task 3: Front-matter parsing and validation

**Files:**
- Create: `tools/playbook/frontmatter.py`
- Test: `tests/test_frontmatter.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `frontmatter.Source(type, name, url)`, `frontmatter.Page(path, title, module, status, tags, sources, reviewed, review_interval, version, generated)` with property `review_due -> date | None`, `frontmatter.Problem(path, field, problem)`, `frontmatter.parse(path: str, text: str) -> tuple[Page | None, list[Problem]]`, `frontmatter.load_all(docs_dir: Path) -> tuple[list[Page], list[Problem]]`, constants `STATUSES`, `DEFAULT_REVIEW_INTERVAL`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_frontmatter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'playbook.frontmatter'`

- [ ] **Step 3: Write the implementation**

```python
# tools/playbook/frontmatter.py
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
```

Note `isinstance(raw_reviewed, date)` catches PyYAML's native date parsing of unquoted `2026-09-07`. The `status == "reviewed"` check guards on `raw_reviewed is None` so a *malformed* date reports one problem, not two.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_frontmatter.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add tools/playbook/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: add front-matter parsing and validation"
```

---

### Task 4: Git history

**Files:**
- Create: `tools/playbook/gitmeta.py`
- Test: `tests/test_gitmeta.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `gitmeta.Commit(sha: str, date: date, subject: str, paths: tuple[str, ...])` where `paths` are posix paths **relative to the docs directory**; `gitmeta.history(repo: Path, docs_dir: Path) -> list[Commit]` newest first; `gitmeta.latest_by_path(commits: list[Commit]) -> dict[str, Commit]`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_gitmeta.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'playbook.gitmeta'`

- [ ] **Step 3: Write the implementation**

```python
# tools/playbook/gitmeta.py
"""Read git history for documentation pages."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RECORD = "\x1e"
FIELD = "\x1f"


@dataclass(frozen=True)
class Commit:
    sha: str
    date: date
    subject: str
    paths: tuple[str, ...]


def history(repo: Path, docs_dir: Path) -> list[Commit]:
    prefix = docs_dir.relative_to(repo).as_posix()
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--no-merges",
                "--date=short",
                f"--format={RECORD}%H{FIELD}%ad{FIELD}%s",
                "--name-only",
                "--",
                prefix,
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return parse_log(result.stdout, prefix=prefix)


def parse_log(output: str, *, prefix: str) -> list[Commit]:
    commits: list[Commit] = []
    for chunk in output.split(RECORD):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        header, _, rest = chunk.partition("\n")
        sha, _, tail = header.partition(FIELD)
        stamp, _, subject = tail.partition(FIELD)
        paths = tuple(
            line[len(prefix) + 1 :]
            for line in rest.splitlines()
            if line.startswith(f"{prefix}/") and line.endswith(".md")
        )
        commits.append(
            Commit(
                sha=sha,
                date=date.fromisoformat(stamp),
                subject=subject,
                paths=paths,
            )
        )
    return commits


def latest_by_path(commits: list[Commit]) -> dict[str, Commit]:
    latest: dict[str, Commit] = {}
    for commit in commits:
        for path in commit.paths:
            latest.setdefault(path, commit)
    return latest
```

One subprocess for the whole tree. The per-file alternative degrades badly past a hundred pages. `latest_by_path` relies on `git log` returning newest first and uses `setdefault` so the first sighting wins.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_gitmeta.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add tools/playbook/gitmeta.py tests/test_gitmeta.py
git commit -m "feat: add git history reader"
```

---

### Task 5: Renderers

Six pure functions from data to markdown. No I/O, no clock reads (today is passed in), no git calls.

**Files:**
- Create: `tools/playbook/pages.py`
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: `frontmatter.Page`, `frontmatter.Source`, `gitmeta.Commit`.
- Produces: `pages.render_references(page) -> str`, `pages.render_page_footer(page) -> str`, `pages.render_adr_index(all_pages) -> str`, `pages.render_recently_updated(all_pages, latest, limit=10) -> str`, `pages.render_changelog(commits, all_pages) -> str`, `pages.render_research_queue(all_pages, today) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pages.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pages.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'playbook.pages'`

- [ ] **Step 3: Write the implementation**

```python
# tools/playbook/pages.py
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
```

Links in generated pages are relative to the docs root because all three generated pages live at `docs/`. ADR index links drop the `decisions/` prefix because `decisions/index.md` sits inside that directory.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pages.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add tools/playbook/pages.py tests/test_pages.py
git commit -m "feat: add markdown renderers"
```

---

### Task 6: Generator CLI — `sync` and `--check`

Writes front-matter-derived blocks into committed sources. This is the half of the generator that CI verifies.

**Files:**
- Create: `tools/generate.py`
- Test: `tests/test_generate_sync.py`

**Interfaces:**
- Consumes: `blocks`, `frontmatter`, `gitmeta`, `pages`.
- Produces: `generate.sync_outputs(docs_dir: Path) -> tuple[dict[Path, str], list[Problem]]`, `generate.write(outputs: dict[Path, str]) -> list[Path]`, `generate.stale(outputs: dict[Path, str]) -> list[Path]`, `generate.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generate_sync.py
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

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
    outputs, problems = generate.sync_outputs(docs)
    assert problems == []
    text = outputs[docs / "modules" / "authentication" / "jwt.md"]
    assert "<!-- generated:references start -->" in text
    assert "[RFC 7519](https://example.test/7519)" in text
    assert "**Review due:** 2027-03-06" in text


def test_sync_reports_problems_and_produces_nothing(docs):
    (docs / "broken.md").write_text("# no front matter\n", encoding="utf-8")
    outputs, problems = generate.sync_outputs(docs)
    assert outputs == {}
    assert [str(problem) for problem in problems] == [
        "broken.md: front-matter: missing or malformed"
    ]


def test_sync_is_idempotent(docs):
    generate.write(generate.sync_outputs(docs)[0])
    first = (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8")
    generate.write(generate.sync_outputs(docs)[0])
    second = (docs / "modules" / "authentication" / "jwt.md").read_text(encoding="utf-8")
    assert first == second


def test_stale_is_empty_after_a_write(docs):
    outputs, _ = generate.sync_outputs(docs)
    generate.write(outputs)
    assert generate.stale(generate.sync_outputs(docs)[0]) == []


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generate_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate'`

- [ ] **Step 3: Write the implementation**

```python
# tools/generate.py
"""Generate derived playbook content.

Two subcommands with different guarantees:

    sync   Writes blocks derived only from front-matter into committed
           sources. Deterministic, so `--check` can verify it in CI.
    build  Writes pages derived from git history and today's date. Those
           pages are gitignored build artifacts, never committed.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from playbook import blocks, frontmatter, gitmeta, pages as renderers


def sync_outputs(docs_dir: Path) -> tuple[dict[Path, str], list[frontmatter.Problem]]:
    parsed, problems = frontmatter.load_all(docs_dir)
    if problems:
        return {}, problems
    outputs: dict[Path, str] = {}
    for page in parsed:
        if page.generated:
            continue
        file = docs_dir / page.path
        text = file.read_text(encoding="utf-8")
        text = blocks.upsert_block(text, "references", renderers.render_references(page))
        text = blocks.upsert_block(text, "page-footer", renderers.render_page_footer(page))
        if page.path == "decisions/index.md":
            text = blocks.upsert_block(
                text, "adr-index", renderers.render_adr_index(parsed)
            )
        outputs[file] = text
    return outputs, []


def stale(outputs: dict[Path, str]) -> list[Path]:
    return [
        path
        for path, text in outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]


def write(outputs: dict[Path, str]) -> list[Path]:
    written = stale(outputs)
    for path in written:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(outputs[path])
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generate")
    parser.add_argument("command", choices=("sync", "build"))
    parser.add_argument("--check", action="store_true",
                        help="report stale files and exit non-zero, writing nothing")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    docs_dir = root / "docs"

    if args.command == "sync":
        outputs, problems = sync_outputs(docs_dir)
    else:
        outputs, problems = build_outputs(root, docs_dir, date.today())

    if problems:
        for problem in problems:
            print(str(problem), file=sys.stderr)
        return 1

    if args.check:
        found = stale(outputs)
        for path in found:
            print(f"stale: {path.relative_to(root).as_posix()}", file=sys.stderr)
        return 1 if found else 0

    for path in write(outputs):
        print(f"wrote: {path.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`build_outputs` is added in Task 7. Until then `generate.py build` raises `NameError`; the `sync` tests do not touch it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_generate_sync.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add tools/generate.py tests/test_generate_sync.py
git commit -m "feat: add generator sync command with check mode"
```

---

### Task 7: Generator `build` command and the dev runner

**Files:**
- Modify: `tools/generate.py` (add `build_outputs` and `GENERATED_PAGES`)
- Create: `tools/dev.py`
- Test: `tests/test_generate_build.py`

**Interfaces:**
- Consumes: `generate.write`, `generate.stale`, `gitmeta.history`, `gitmeta.latest_by_path`, all six renderers.
- Produces: `generate.build_outputs(root: Path, docs_dir: Path, today: date) -> tuple[dict[Path, str], list[Problem]]`; `tools/dev.py` commands `gen`, `check`, `serve`, `build`, `page`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generate_build.py
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

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
```

`test_build_output_reparses_cleanly` is the guard that generated pages satisfy their own validator — otherwise the second run of `sync` fails on files the generator itself wrote.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generate_build.py -v`
Expected: FAIL — `AttributeError: module 'generate' has no attribute 'build_outputs'`

- [ ] **Step 3: Add `build_outputs` to `tools/generate.py`**

Insert after `sync_outputs`:

```python
GENERATED_PAGES = {
    "recently-updated.md": "Recently updated",
    "changelog.md": "Changelog",
    "research-queue.md": "Research queue",
}


def build_outputs(
    root: Path, docs_dir: Path, today: date
) -> tuple[dict[Path, str], list[frontmatter.Problem]]:
    parsed, problems = frontmatter.load_all(docs_dir)
    if problems:
        return {}, problems
    commits = gitmeta.history(root, docs_dir)
    latest = gitmeta.latest_by_path(commits)
    bodies = {
        "recently-updated.md": renderers.render_recently_updated(parsed, latest),
        "changelog.md": renderers.render_changelog(commits, parsed),
        "research-queue.md": renderers.render_research_queue(parsed, today),
    }
    outputs: dict[Path, str] = {}
    for name, body in bodies.items():
        title = GENERATED_PAGES[name]
        outputs[docs_dir / name] = (
            f"---\ntitle: {title}\ngenerated: true\n---\n\n# {title}\n\n{body}\n"
        )
    return outputs, []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_generate_build.py -v`
Expected: 7 passed

- [ ] **Step 5: Write the dev runner**

```python
# tools/dev.py
"""Cross-platform task runner. Replaces a Makefile, which Git Bash lacks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "tools" / "templates"


def run(*args: str) -> int:
    return subprocess.run(list(args), cwd=ROOT).returncode


def gen() -> int:
    return run(sys.executable, "tools/generate.py", "sync") or run(
        sys.executable, "tools/generate.py", "build"
    )


def check() -> int:
    return run(sys.executable, "-m", "pytest", "-q") or run(
        sys.executable, "tools/generate.py", "sync", "--check"
    )


def serve() -> int:
    return gen() or run("zensical", "serve")


def build() -> int:
    return gen() or run("zensical", "build", "--clean")


def page(kind: str, path: str, title: str, module: str) -> int:
    template = TEMPLATES / f"{kind}.md"
    if not template.exists():
        print(f"unknown template kind: {kind}", file=sys.stderr)
        return 1
    target = ROOT / "docs" / path
    if target.exists():
        print(f"refusing to overwrite: {path}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    text = (
        template.read_text(encoding="utf-8")
        .replace("{{TITLE}}", title)
        .replace("{{MODULE}}", module)
    )
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"created: docs/{path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="dev")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("gen", "check", "serve", "build"):
        sub.add_parser(name)
    page_parser = sub.add_parser("page")
    page_parser.add_argument("--kind", required=True,
                             choices=("module", "subpage", "adr", "checklist", "matrix"))
    page_parser.add_argument("--path", required=True)
    page_parser.add_argument("--title", required=True)
    page_parser.add_argument("--module", required=True)
    args = parser.parse_args()
    if args.command == "page":
        return page(args.kind, args.path, args.title, args.module)
    return {"gen": gen, "check": check, "serve": serve, "build": build}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
```

`run(...) or run(...)` short-circuits on a non-zero exit code, so a failing step stops the chain.

- [ ] **Step 6: Verify the runner end to end**

Run: `uv run python tools/dev.py gen`
Expected: exit 0, and `docs/recently-updated.md`, `docs/changelog.md`, `docs/research-queue.md` now exist and are gitignored (`git status --short` shows none of them).

Run: `uv run python tools/dev.py check`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add tools/generate.py tools/dev.py tests/test_generate_build.py
git commit -m "feat: add build command and cross-platform dev runner"
```

---

### Task 8: Page templates

**Files:**
- Create: `tools/templates/module.md`
- Create: `tools/templates/subpage.md`
- Create: `tools/templates/adr.md`
- Create: `tools/templates/checklist.md`
- Create: `tools/templates/matrix.md`

**Interfaces:**
- Consumes: `dev.py page` substitutes `{{TITLE}}` and `{{MODULE}}`.
- Produces: the section structure every content task fills in.

- [ ] **Step 1: Write `tools/templates/module.md`**

```markdown
---
title: {{TITLE}}
module: {{MODULE}}
status: stub
tags: []
sources: []
---

# {{TITLE}}

## Executive summary

### Purpose

### When to use

### When not to use

## Architecture overview

``` mermaid
sequenceDiagram
  autonumber
```

## Flow diagram

## Functional requirements

## Non-functional requirements

## Pros and cons

## Alternatives

## Security considerations

## Implementation examples

## Common mistakes

## Real-world implementations

## References
```

- [ ] **Step 2: Write `tools/templates/subpage.md`**

```markdown
---
title: {{TITLE}}
module: {{MODULE}}
status: stub
tags: []
sources: []
---

# {{TITLE}}

## Executive summary

### Purpose

### When to use

### When not to use

## How it works

``` mermaid
sequenceDiagram
  autonumber
```

## Pros and cons

## Alternatives

## Security considerations

## Implementation examples

## Common mistakes

## References
```

- [ ] **Step 3: Write `tools/templates/adr.md`**

```markdown
---
title: {{TITLE}}
module: {{MODULE}}
status: stub
tags: [ADR]
sources: []
---

# {{TITLE}}

## Context

## Decision

## Consequences

### Positive

### Negative

## Alternatives considered

## Migration path

## References
```

- [ ] **Step 4: Write `tools/templates/checklist.md`**

```markdown
---
title: {{TITLE}}
module: {{MODULE}}
status: stub
tags: [Checklist]
sources: []
---

# {{TITLE}}

Every item maps to authoritative guidance so the baseline is industry
standard rather than opinion.

## Before launch

- [ ] Item — _why_ — [source](https://example.test)

## Ongoing

- [ ] Item — _why_ — [source](https://example.test)

## References
```

- [ ] **Step 5: Write `tools/templates/matrix.md`**

```markdown
---
title: {{TITLE}}
module: {{MODULE}}
status: stub
tags: [Decision matrix]
sources: []
---

# {{TITLE}}

{{ read_csv('data/decisions/CHANGE-ME.csv') }}

## Why

## Tradeoffs

## Migration path

## References
```

- [ ] **Step 6: Verify a template produces a valid page**

Run:
```bash
uv run python tools/dev.py page --kind subpage --path modules/authentication/scratch.md --title "Scratch" --module authentication
uv run python tools/generate.py sync
```
Expected: exit 0 both times. Open `docs/modules/authentication/scratch.md` and confirm the references and page-footer blocks were appended.

Then delete it: `rm docs/modules/authentication/scratch.md`

- [ ] **Step 7: Commit**

```bash
git add tools/templates
git commit -m "feat: add page templates"
```

---

### Task 9: Documentation skeleton and navigation

Creates every page the v1 nav references, so the site builds with link validation on. Content depth comes in Tasks 11 and 12.

**Files:**
- Modify: `zensical.toml` (nav, site URLs, extra CSS)
- Create: `docs/index.md` (replaces the smoke-test version)
- Create: `docs/principles/index.md` and 9 principle pages
- Create: `docs/modules/index.md` and 7 module `index.md` files
- Create: `docs/security/index.md` and 15 security pages
- Create: `docs/decisions/index.md`, `docs/checklists/index.md`, `docs/matrices/index.md`
- Create: `docs/stylesheets/extra.css`

- [ ] **Step 1: Create the principle pages**

Nine files under `docs/principles/`, one per principle: `security-first.md`, `api-first.md`, `cloud-native.md`, `twelve-factor.md`, `multi-tenant-design.md`, `least-privilege.md`, `defense-in-depth.md`, `event-driven-architecture.md`, `domain-driven-design.md`.

Each uses this exact shape, with `{{TITLE}}` replaced by the principle's display name:

```markdown
---
title: {{TITLE}}
module: principles
status: stub
tags: [Principles]
sources: []
---

# {{TITLE}}

## What it means

## Why it matters

## How it shows up in this playbook

## References
```

Display names: Security first, API first, Cloud native, Twelve-factor app, Multi-tenant design, Least privilege, Defense in depth, Event-driven architecture, Domain-driven design.

And `docs/principles/index.md`:

```markdown
---
title: Engineering principles
module: principles
status: draft
tags: [Principles]
sources: []
---

# Engineering principles

The commitments every module in this playbook is written against. Modules
link here rather than restating them.

<div class="grid cards" markdown>

-   __[Security first](security-first.md)__

    ---

    Threat model before feature work.

-   __[API first](api-first.md)__

    ---

    The contract is the product.

-   __[Cloud native](cloud-native.md)__

    ---

    Disposable, observable, horizontally scaled.

-   __[Twelve-factor app](twelve-factor.md)__

    ---

    Config in environment, stateless processes.

-   __[Multi-tenant design](multi-tenant-design.md)__

    ---

    Isolation is a design property, not a filter.

-   __[Least privilege](least-privilege.md)__

    ---

    Grant the minimum, expire it by default.

-   __[Defense in depth](defense-in-depth.md)__

    ---

    Assume every single control fails.

-   __[Event-driven architecture](event-driven-architecture.md)__

    ---

    Decouple through facts, not calls.

-   __[Domain-driven design](domain-driven-design.md)__

    ---

    Model the business, not the database.

</div>
```

- [ ] **Step 2: Create the module index pages**

Seven directories under `docs/modules/`, each containing only `index.md` for now: `authentication`, `authorization`, `multi-tenancy`, `api-design`, `database-design`, `networking`, `observability`.

Use `tools/templates/module.md` for each via the runner, for example:

```bash
uv run python tools/dev.py page --kind module --path modules/authorization/index.md --title "Authorization" --module authorization
```

Titles: Authentication, Authorization, Multi-tenancy, API design, Database design, Networking, Observability.

Then `docs/modules/index.md`:

```markdown
---
title: Architecture library
module: modules
status: draft
tags: [Modules]
sources: []
---

# Architecture library

Each module is a complete implementation guide: what the options are, how to
build them, why one was chosen, and how to verify it.

<div class="grid cards" markdown>

-   __[Authentication](authentication/index.md)__

    ---

    Login, registration, MFA, password hashing, OAuth, SSO.

-   __[Authorization](authorization/index.md)__

    ---

    Roles, permissions, policy engines, inheritance.

-   __[Multi-tenancy](multi-tenancy/index.md)__

    ---

    Tenant isolation, database strategies, scaling.

-   __[API design](api-design/index.md)__

    ---

    REST, GraphQL, gRPC, versioning.

-   __[Database design](database-design/index.md)__

    ---

    ERDs, indexing, migrations.

-   __[Networking](networking/index.md)__

    ---

    Reverse proxy, load balancers, TLS.

-   __[Observability](observability/index.md)__

    ---

    Logging, tracing, metrics.

-   __[Security](../security/index.md)__

    ---

    The security playbook. Lives in its own section, not duplicated here.

</div>
```

- [ ] **Step 3: Create the security section**

Fifteen files under `docs/security/`: `password-storage.md`, `session-security.md`, `secrets-management.md`, `encryption.md`, `api-security.md`, `oauth-security.md`, `owasp-top-10.md`, `audit-logging.md`, `rate-limiting.md`, `mfa.md`, `sso.md`, `secure-headers.md`, `key-rotation.md`, `backup-strategy.md`, `incident-response.md`.

Each uses this exact shape:

```markdown
---
title: {{TITLE}}
module: security
status: stub
tags: [Security]
sources: []
---

# {{TITLE}}

## Executive summary

## Threats addressed

## Implementation guidance

## Verification

## Common mistakes

## References
```

Titles: Password storage, Session security, Secrets management, Encryption, API security, OAuth security, OWASP Top 10, Audit logging, Rate limiting, MFA, SSO, Secure headers, Key rotation, Backup strategy, Incident response.

And `docs/security/index.md`:

```markdown
---
title: Security playbook
module: security
status: draft
tags: [Security]
sources: []
---

# Security playbook

The single home for security guidance. Modules link here; nothing security
related is duplicated inside a module page.

Every page maps its guidance to an authoritative baseline — primarily the
[OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — so the
playbook inherits an industry standard instead of accumulating opinion.

- [Password storage](password-storage.md)
- [Session security](session-security.md)
- [Secrets management](secrets-management.md)
- [Encryption](encryption.md)
- [API security](api-security.md)
- [OAuth security](oauth-security.md)
- [OWASP Top 10](owasp-top-10.md)
- [Audit logging](audit-logging.md)
- [Rate limiting](rate-limiting.md)
- [MFA](mfa.md)
- [SSO](sso.md)
- [Secure headers](secure-headers.md)
- [Key rotation](key-rotation.md)
- [Backup strategy](backup-strategy.md)
- [Incident response](incident-response.md)
```

- [ ] **Step 4: Create the decisions, checklists and matrices index pages**

`docs/decisions/index.md` — note the ADR index block is filled by the generator:

```markdown
---
title: Decision records
module: decisions
status: draft
tags: [ADR]
sources: []
---

# Decision records

Why one approach was chosen over the alternatives, with the migration path
out if the decision stops holding.

<!-- generated:adr-index start -->
_No decision records yet._
<!-- generated:adr-index end -->
```

`docs/checklists/index.md`:

```markdown
---
title: Production checklists
module: checklists
status: draft
tags: [Checklist]
sources: []
---

# Production checklists

How to verify an implementation before it ships.

- [Authentication](authentication.md)
```

`docs/matrices/index.md`:

```markdown
---
title: Decision matrices
module: matrices
status: draft
tags: [Decision matrix]
sources: []
---

# Decision matrices

Scored comparisons for choices made under time pressure. Each matrix reads
its data from a CSV file, so the comparison stays structured and diffable.

- [Password hashing](password-hashing.md)
- [JWT vs session cookies](jwt-vs-session-cookies.md)
```

Both linked matrix pages are created in Task 11. Until then the build will
warn about invalid links — expected, and resolved by Task 11. Create
`docs/checklists/authentication.md` and the two matrix pages as empty stubs
now if you want a clean build in between:

```bash
uv run python tools/dev.py page --kind checklist --path checklists/authentication.md --title "Authentication checklist" --module authentication
uv run python tools/dev.py page --kind matrix --path matrices/password-hashing.md --title "Password hashing" --module authentication
uv run python tools/dev.py page --kind matrix --path matrices/jwt-vs-session-cookies.md --title "JWT vs session cookies" --module authentication
```

- [ ] **Step 5: Write the dashboard**

`docs/index.md`, replacing the smoke-test version:

```markdown
---
title: Engineering Playbook
module: home
status: draft
tags: [Playbook]
sources: []
---

# Engineering Playbook

A living architecture playbook: what the options are, how to build them, why
one was chosen, and how to verify it before it ships.

<div class="grid cards" markdown>

-   __[Principles](principles/index.md)__

    ---

    The commitments every module is written against.

-   __[Architecture library](modules/index.md)__

    ---

    Complete implementation guides, module by module.

-   __[Security playbook](security/index.md)__

    ---

    Threats, controls, and verification, mapped to OWASP.

-   __[Decision records](decisions/index.md)__

    ---

    Why one approach won, and the way back out.

-   __[Production checklists](checklists/index.md)__

    ---

    Verification before shipping.

-   __[Decision matrices](matrices/index.md)__

    ---

    Scored comparisons for choices under time pressure.

</div>

## What's moving

-   __[Recently updated](recently-updated.md)__ — what changed and when
-   __[Changelog](changelog.md)__ — every change, grouped by month
-   __[Research queue](research-queue.md)__ — stubs and pages past their review date
```

The dashboard links to the three generated pages rather than embedding their
content, so `index.md` is never rewritten at build time and stays free of
git-derived drift.

- [ ] **Step 6: Write `docs/stylesheets/extra.css`**

```css
/* Give generated tables room to breathe on wide pages. */
.md-typeset table:not([class]) {
  font-size: 0.75rem;
}
```

- [ ] **Step 7: Add nav, site URLs and CSS to `zensical.toml`**

Replace `<user>` with the actual GitHub username. Add to the `[project]` table:

```toml
site_url  = "https://<user>.github.io/engineering-playbook/"
repo_url  = "https://github.com/<user>/engineering-playbook"
repo_name = "<user>/engineering-playbook"
edit_uri  = "edit/main/docs/"
extra_css = ["stylesheets/extra.css"]
watch     = ["data", "tools"]

nav = [
  { "Playbook" = "index.md" },
  { "Principles" = [
    "principles/index.md",
    "principles/security-first.md",
    "principles/api-first.md",
    "principles/cloud-native.md",
    "principles/twelve-factor.md",
    "principles/multi-tenant-design.md",
    "principles/least-privilege.md",
    "principles/defense-in-depth.md",
    "principles/event-driven-architecture.md",
    "principles/domain-driven-design.md",
  ] },
  { "Modules" = [
    "modules/index.md",
    { "Authentication" = [
      "modules/authentication/index.md",
      "modules/authentication/email-password.md",
      "modules/authentication/magic-link.md",
      "modules/authentication/passkeys.md",
      "modules/authentication/social-login.md",
      "modules/authentication/enterprise-sso.md",
      "modules/authentication/oidc.md",
      "modules/authentication/oauth2.md",
      "modules/authentication/jwt.md",
      "modules/authentication/session-cookies.md",
      "modules/authentication/refresh-tokens.md",
    ] },
    "modules/authorization/index.md",
    "modules/multi-tenancy/index.md",
    "modules/api-design/index.md",
    "modules/database-design/index.md",
    "modules/networking/index.md",
    "modules/observability/index.md",
  ] },
  { "Security" = [
    "security/index.md",
    "security/password-storage.md",
    "security/session-security.md",
    "security/secrets-management.md",
    "security/encryption.md",
    "security/api-security.md",
    "security/oauth-security.md",
    "security/owasp-top-10.md",
    "security/audit-logging.md",
    "security/rate-limiting.md",
    "security/mfa.md",
    "security/sso.md",
    "security/secure-headers.md",
    "security/key-rotation.md",
    "security/backup-strategy.md",
    "security/incident-response.md",
  ] },
  { "Decisions" = [ "decisions/index.md" ] },
  { "Checklists" = [ "checklists/index.md", "checklists/authentication.md" ] },
  { "Matrices" = [
    "matrices/index.md",
    "matrices/password-hashing.md",
    "matrices/jwt-vs-session-cookies.md",
  ] },
  { "What's moving" = [
    "recently-updated.md",
    "changelog.md",
    "research-queue.md",
  ] },
]
```

The ten authentication subpages are listed in nav but created in Task 12. Build will warn until then.

- [ ] **Step 8: Generate, build and check**

Run: `uv run python tools/dev.py gen`
Expected: exit 0. `docs/research-queue.md` now lists every stub page.

Run: `uv run zensical build --clean`
Expected: exit 0. Warnings only for the not-yet-created authentication subpages.

Run: `uv run python tools/dev.py check`
Expected: exit 0.

- [ ] **Step 9: Commit**

```bash
git add zensical.toml docs
git commit -m "feat: add documentation skeleton and navigation"
```

---

### Task 10: Continuous integration and GitHub Pages

**Files:**
- Create: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: `tools/generate.py`, `pyproject.toml`, `uv.lock`.
- Produces: a deployed site at `https://<user>.github.io/engineering-playbook/`.

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/docs.yml
name: Documentation

on:
  push:
    branches:
      - main
  pull_request:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # full history: the changelog is derived from it
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --locked
      - name: Test and verify generated content is current
        run: uv run python tools/dev.py check
      - name: Generate build-time pages
        run: uv run python tools/generate.py build
      - run: uv run zensical build --clean
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

`fetch-depth: 0` is load-bearing: the default shallow clone gives one commit, so the changelog and recently-updated pages would be near-empty. `dev.py check` runs the tests and the `sync --check` verification; the build-time generation runs after, because it intentionally writes files that are not committed.

- [ ] **Step 2: Push and enable Pages**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: build and deploy to github pages"
git push -u origin main
```

Then in the GitHub repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

- [ ] **Step 3: Verify the deployment**

Watch the workflow run to completion. Open the deployed URL. Confirm the dashboard renders, search works, and the changelog page contains real commits (not `_No history yet._` — if it does, `fetch-depth` is wrong).

- [ ] **Step 4: Verify the check gate actually fails**

Locally, edit a page's `status` from `stub` to `draft` without running the generator, commit and push to a branch, and open a pull request. The `build` job must fail with `stale: docs/...`. Then run `uv run python tools/dev.py gen`, commit, and confirm it passes.

This confirms the gate works. A check that never fails is not a check.

---

### Task 11: Authentication module overview, checklist, matrices and ADR

**Files:**
- Modify: `docs/modules/authentication/index.md`
- Modify: `docs/checklists/authentication.md`
- Modify: `docs/matrices/password-hashing.md`
- Modify: `docs/matrices/jwt-vs-session-cookies.md`
- Create: `data/decisions/password-hashing.csv`
- Create: `data/decisions/jwt-vs-session-cookies.csv`
- Create: `docs/decisions/0001-argon2id-for-password-hashing.md`
- Modify: `zensical.toml` (add the ADR to nav)

- [ ] **Step 1: Write the two CSV data files**

`data/decisions/password-hashing.csv`:

```csv
Option,Resistance to GPU attack,Memory hard,Standardized,Score,Verdict
Argon2id,Strong,Yes,RFC 9106,5,Default choice
scrypt,Strong,Yes,RFC 7914,4,Good where Argon2id is unavailable
bcrypt,Moderate,No,De facto,3,Acceptable legacy; 72-byte input limit
PBKDF2,Weak,No,NIST SP 800-132,2,Only when FIPS compliance forces it
```

`data/decisions/jwt-vs-session-cookies.csv`:

```csv
Criterion,JWT (stateless),Session cookie (server state)
Revocation,Hard — token valid until expiry,Easy — delete the session
Horizontal scale,No shared store needed,Needs shared session store
Payload size,Grows with claims,Opaque identifier only
XSS exposure,High if stored in localStorage,Low with HttpOnly
Logout semantics,Needs a denylist,Immediate
Best fit,Short-lived service-to-service,Browser-facing applications
```

- [ ] **Step 2: Write the matrix pages**

`docs/matrices/password-hashing.md`:

```markdown
---
title: Password hashing
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Decision matrix, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
  - { type: standard, name: "OWASP Password Storage Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html" }
---

# Password hashing

{{ read_csv('data/decisions/password-hashing.csv') }}

## Why

Password hashing is chosen for how badly it performs on an attacker's
hardware. Argon2id wins because it is memory hard: an attacker cannot trade
cheap parallel compute for the memory the algorithm demands, which is exactly
the advantage GPUs and ASICs otherwise have.

## Tradeoffs

Memory hardness costs the defender memory too. Tune the parameters against
your own hardware and keep verification within the latency budget.

## Migration path

Rehash on successful login: verify against the old algorithm, then write a
fresh Argon2id hash. Store the algorithm alongside the hash so both can
coexist during the transition. Never bulk-rehash — you do not have the
plaintext.

See [Use Argon2id for password hashing](../decisions/0001-argon2id-for-password-hashing.md).

## References
```

`docs/matrices/jwt-vs-session-cookies.md`:

```markdown
---
title: JWT vs session cookies
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Decision matrix, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 7519 — JSON Web Token", url: "https://www.rfc-editor.org/rfc/rfc7519" }
  - { type: standard, name: "OWASP Session Management Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html" }
---

# JWT vs session cookies

{{ read_csv('data/decisions/jwt-vs-session-cookies.csv') }}

## Why

The decision is about revocation, not about tokens. A JWT is a bearer
credential you cannot take back before it expires; a session identifier is a
lookup you can delete. Everything else follows from that.

## Tradeoffs

Statelessness buys horizontal scale and costs you immediate logout. Most
applications that adopt JWTs then rebuild session state as a denylist, which
is the state they were avoiding, with worse ergonomics.

## Migration path

Shorten the access token lifetime first, then introduce refresh tokens with
rotation, then move browser-facing sessions to `HttpOnly` cookies.

## References
```

- [ ] **Step 3: Write the ADR**

`docs/decisions/0001-argon2id-for-password-hashing.md`:

```markdown
---
title: Use Argon2id for password hashing
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [ADR, Authentication, Security]
sources:
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
  - { type: standard, name: "OWASP Password Storage Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html" }
---

# Use Argon2id for password hashing

## Context

Password storage must stay expensive for an attacker holding a stolen
database and cheap enough for a login request. bcrypt has served this role
but is not memory hard and silently truncates input past 72 bytes. PBKDF2 is
weakest against parallel hardware and is chosen almost entirely for
compliance reasons.

## Decision

Argon2id is the default for all new password storage, with parameters tuned
so verification stays under 500 ms on production hardware.

## Consequences

### Positive

Memory hardness removes the attacker's parallel-hardware advantage. Argon2id
combines Argon2i's side-channel resistance with Argon2d's GPU resistance.
The algorithm is standardized in RFC 9106 and recommended first by OWASP.

### Negative

Verification consumes real memory per concurrent login, which constrains how
many logins a node handles at once. Parameters must be re-tuned when hardware
changes, and that re-tuning is easy to forget.

## Alternatives considered

See [the password hashing matrix](../matrices/password-hashing.md).

## Migration path

Rehash opportunistically on successful login. Store the algorithm identifier
with each hash so both schemes coexist during the transition.

## References
```

- [ ] **Step 4: Write the authentication checklist**

`docs/checklists/authentication.md`:

```markdown
---
title: Authentication checklist
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Checklist, Authentication, Security]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: standard, name: "OWASP Session Management Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html" }
---

# Authentication checklist

Every item maps to authoritative guidance so the baseline is industry
standard rather than opinion.

## Credential storage

- [ ] Passwords hashed with Argon2id — memory hardness defeats parallel cracking — [matrix](../matrices/password-hashing.md)
- [ ] Verification stays under 500 ms — a login must not become a denial-of-service lever
- [ ] No password length cap below 64 characters — caps push users toward weaker secrets
- [ ] Passwords checked against a breached-password list — reuse is the dominant real-world failure

## Session handling

- [ ] Session cookie is `HttpOnly` — script cannot read it, so XSS cannot steal it
- [ ] Session cookie is `Secure` — never transmitted over plaintext
- [ ] `SameSite=Lax` at minimum — blunts cross-site request forgery
- [ ] Session identifier is rotated on privilege change — defeats session fixation
- [ ] Logout invalidates server-side state — not just the cookie
- [ ] Idle timeout of 8 hours, absolute timeout enforced separately

## Multi-factor

- [ ] MFA is available to every account, not only administrators
- [ ] TOTP secrets encrypted at rest
- [ ] Recovery codes are single use and regenerated after use
- [ ] Enrolling or removing a factor triggers a notification to the account owner

## Rate limiting and lockout

- [ ] Login attempts limited per account and per source address
- [ ] Failures produce a uniform response — distinct errors enumerate valid accounts
- [ ] Password reset tokens are single use with a short expiry

## Verification

- [ ] Every item above has a test that fails when the control is removed

## References
```

- [ ] **Step 5: Write the authentication module overview**

`docs/modules/authentication/index.md` — replace the template stub. Set front-matter first:

```yaml
---
title: Authentication
module: authentication
status: reviewed
reviewed: 2026-09-07
tags: [Authentication, Security]
sources:
  - { type: standard, name: "OWASP Authentication Cheat Sheet", url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html" }
  - { type: rfc, name: "RFC 6749 — OAuth 2.0", url: "https://www.rfc-editor.org/rfc/rfc6749" }
  - { type: rfc, name: "RFC 9106 — Argon2", url: "https://www.rfc-editor.org/rfc/rfc9106" }
---
```

Body sections, following `tools/templates/module.md`. Write real prose in each; the three mermaid diagrams below are required and must render.

Login flow:

```` markdown
``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant DB as User store
  User->>App: POST /login (email, password)
  App->>Auth: verify(email, password)
  Auth->>DB: fetch password hash
  DB-->>Auth: argon2id hash
  Auth->>Auth: verify hash (constant time)
  alt credentials valid
    Auth->>Auth: create session
    Auth-->>App: session id
    App-->>User: 200 + Set-Cookie (HttpOnly, Secure, SameSite=Lax)
  else credentials invalid
    Auth-->>App: failure
    App-->>User: 401 (uniform message)
  end
```
````

Password reset flow:

```` markdown
``` mermaid
sequenceDiagram
  autonumber
  actor User
  participant App as Application
  participant Auth as Auth service
  participant Mail as Mail service
  User->>App: POST /forgot (email)
  App->>Auth: issue reset token
  Auth->>Auth: single-use token, short expiry
  Auth->>Mail: send reset link
  App-->>User: 200 (uniform message, always)
  User->>App: GET /reset?token
  App->>Auth: validate token
  Auth-->>App: valid
  User->>App: POST /reset (new password)
  App->>Auth: rehash + invalidate all sessions
  Auth-->>App: done
  App-->>User: 200 + new session
```
````

Refresh token flow:

```` markdown
``` mermaid
sequenceDiagram
  autonumber
  participant Client
  participant Auth as Auth service
  participant Store as Token store
  Client->>Auth: POST /token (refresh token)
  Auth->>Store: look up token family
  alt token already used
    Auth->>Store: revoke entire family
    Auth-->>Client: 401 (reuse detected)
  else token valid
    Auth->>Store: rotate — mark used, issue successor
    Auth-->>Client: new access + refresh token
  end
```
````

The requirements sections use the source concept's examples:

```markdown
## Functional requirements

- Users can register with email and password
- Users can log in and log out
- Users can reset a forgotten password
- Users can change a known password
- Users can enable and disable MFA
- Users can see and revoke active sessions

## Non-functional requirements

- 99.9% availability for the login path
- Login response under 300 ms at the 95th percentile
- Password verification under 500 ms
- Idle session timeout of 8 hours
```

The module page must link to every subpage, to `../../security/password-storage.md`, to `../../checklists/authentication.md`, and to both matrices.

- [ ] **Step 6: Add the ADR to nav**

In `zensical.toml`, change the Decisions entry to:

```toml
  { "Decisions" = [
    "decisions/index.md",
    "decisions/0001-argon2id-for-password-hashing.md",
  ] },
```

- [ ] **Step 7: Generate, build and verify**

Run: `uv run python tools/dev.py gen`
Expected: exit 0. `docs/decisions/index.md` now lists the ADR in its generated block.

Run: `uv run zensical build --clean`
Expected: exit 0, warnings only for the ten not-yet-written subpages.

Run: `uv run zensical serve` and confirm both CSV tables render as tables (not as literal `{{ read_csv(...) }}` text) and all three mermaid diagrams render as diagrams.

If `read_csv` renders literally, `table-reader` is misconfigured — fix it here, because Task 12 depends on nothing else from this task.

If the table renders as a "file not found" error instead, the plugin is
resolving `data/decisions/...` against the wrong root. `table-reader`
resolves relative paths against a configurable base. Set it explicitly in
`zensical.toml` rather than guessing:

```toml
[project.plugins.table-reader]
base_path = "config_dir"
```

`config_dir` resolves against the directory holding `zensical.toml` (the
project root), which is what the `data/decisions/...` paths above assume. The
alternative value is `docs_dir`; if you use it, the CSV paths must become
`../data/decisions/...`.

- [ ] **Step 8: Commit**

```bash
git add data docs zensical.toml
git commit -m "feat: add authentication overview, checklist, matrices and first ADR"
```

---

### Task 12: Authentication subpages

The ten subpages that make Authentication a complete implementation guide rather than an outline. This is the task that proves the template survives real depth.

**Files:**
- Create: `docs/modules/authentication/email-password.md`
- Create: `docs/modules/authentication/magic-link.md`
- Create: `docs/modules/authentication/passkeys.md`
- Create: `docs/modules/authentication/social-login.md`
- Create: `docs/modules/authentication/enterprise-sso.md`
- Create: `docs/modules/authentication/oidc.md`
- Create: `docs/modules/authentication/oauth2.md`
- Create: `docs/modules/authentication/jwt.md`
- Create: `docs/modules/authentication/session-cookies.md`
- Create: `docs/modules/authentication/refresh-tokens.md`

- [ ] **Step 1: Scaffold all ten pages**

```bash
uv run python tools/dev.py page --kind subpage --path modules/authentication/email-password.md --title "Email and password" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/magic-link.md --title "Magic link" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/passkeys.md --title "Passkeys" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/social-login.md --title "Social login" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/enterprise-sso.md --title "Enterprise SSO" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/oidc.md --title "OIDC" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/oauth2.md --title "OAuth 2.0" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/jwt.md --title "JWT" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/session-cookies.md --title "Session cookies" --module authentication
uv run python tools/dev.py page --kind subpage --path modules/authentication/refresh-tokens.md --title "Refresh tokens" --module authentication
```

- [ ] **Step 2: Write each page to completion**

Each page fills every section of `tools/templates/subpage.md`, sets `status: reviewed` with `reviewed: 2026-09-07`, and carries at least two entries in `sources` — one standard or RFC, one vendor or implementation reference.

Required source anchors per page:

| Page | Required sources |
| --- | --- |
| Email and password | OWASP Authentication Cheat Sheet; OWASP Password Storage Cheat Sheet |
| Magic link | OWASP Authentication Cheat Sheet; RFC 6238 (where TOTP is contrasted) |
| Passkeys | W3C Web Authentication Level 3; FIDO Alliance passkey guidance |
| Social login | RFC 6749 (OAuth 2.0); RFC 6819 (OAuth threat model) |
| Enterprise SSO | OASIS SAML 2.0 core; Microsoft Entra conditional access documentation |
| OIDC | OpenID Connect Core 1.0; RFC 6749 |
| OAuth 2.0 | RFC 6749; RFC 7636 (PKCE) |
| JWT | RFC 7519; OWASP JSON Web Token Cheat Sheet |
| Session cookies | RFC 6265bis; OWASP Session Management Cheat Sheet |
| Refresh tokens | RFC 6749 §1.5; OAuth 2.0 Security Best Current Practice |

Each page's **Common mistakes** section states the mistake, why it is
dangerous, and the safer alternative. The JWT page must include the
localStorage mistake named in the source concept:

```markdown
## Common mistakes

### Storing a JWT in `localStorage`

Any script running on the page can read `localStorage`. A single XSS flaw
therefore yields a bearer token that works from anywhere until it expires,
and you cannot revoke it.

Store the token in an `HttpOnly`, `Secure`, `SameSite` cookie, or keep it in
memory only and rely on a refresh token in an `HttpOnly` cookie.
```

Each page's **Real-world implementations** section names at least one
production system and what it does differently — GitHub's device
verification and personal access tokens, Google's risk-based authentication
and passkey rollout, or Microsoft Entra's conditional access. These make the
pattern memorable, which is the point of the section.

Every page links back to `index.md` and to the relevant security page under
`../../security/`.

- [ ] **Step 3: Verify no page was left as a stub**

Run: `uv run python tools/generate.py build`
Then open `docs/research-queue.md`. No `modules/authentication/` page may appear in it. If one does, it is still `status: stub` and is not finished.

- [ ] **Step 4: Build and check**

Run: `uv run zensical build --clean`
Expected: exit 0 with **no** link warnings — every nav entry now exists.

Run: `uv run python tools/dev.py check`
Expected: exit 0.

- [ ] **Step 5: Preview and read it as a reader would**

Run: `uv run zensical serve`

Confirm: every mermaid diagram renders; search returns the subpages by topic; hovering a cross-link shows an instant preview; the tag pages list the authentication pages; each page footer shows status, last reviewed and review due.

- [ ] **Step 6: Commit and push**

```bash
git add docs
git commit -m "feat: complete authentication module subpages"
git push
```

- [ ] **Step 7: Verify the deployment**

Watch the workflow. Open the deployed site. Confirm the changelog page now
groups real commits by month and the recently-updated page lists the
authentication pages.

v1 is complete when this passes.

---

### Task 13: Authoring prompts

The four Claude roles from the spec, as plain files you run by hand. Written
after Task 12 deliberately: having just authored eleven pages, you know what
you actually needed to ask for, so these describe a real workflow rather than
a guessed one.

**Files:**
- Create: `prompts/research-agent.md`
- Create: `prompts/architecture-reviewer.md`
- Create: `prompts/documentation-writer.md`
- Create: `prompts/freshness-auditor.md`
- Create: `prompts/README.md`

- [ ] **Step 1: Write `prompts/research-agent.md`**

```markdown
# Role: research agent

Gather authoritative guidance on **<TOPIC>** for the engineering playbook.

Sources, in priority order:

1. OWASP Cheat Sheet Series
2. RFCs and W3C or OASIS specifications
3. Vendor engineering documentation (Microsoft, Google, Cloudflare, AWS)
4. Peer-reviewed research

Do not write documentation. Produce only:

- **Findings** — what current guidance says, each with the claim stated plainly
- **Citations** — type, name and URL for every finding, in the shape used by
  the `sources` front-matter field
- **What changed** — where current guidance differs from what was widely
  recommended three years ago, and why

Flag any finding where sources disagree. Do not resolve the disagreement;
report it.
```

- [ ] **Step 2: Write `prompts/architecture-reviewer.md`**

```markdown
# Role: architecture reviewer

Compare the implementation described below against the playbook's guidance
for **<MODULE>**, and against the checklist at
`docs/checklists/<MODULE>.md`.

Produce:

- **Gaps** — checklist items the implementation does not satisfy
- **Risks** — what an attacker or an outage does with each gap, concretely
- **Improvements** — ordered by risk reduced per unit of work

Cite the playbook page or checklist item behind every finding. If the
playbook has no guidance covering something you found, say so — that is a
research queue entry, not a review finding.
```

- [ ] **Step 3: Write `prompts/documentation-writer.md`**

```markdown
# Role: documentation writer

Convert the research output below into a playbook page.

- Use the template at `tools/templates/subpage.md` (or `module.md` for a
  module overview). Fill every section; delete none.
- Front-matter: set `title`, `module`, `status: draft`, `tags`, and every
  `sources` entry from the research citations.
- Do not write the `references` or `page-footer` blocks — the generator owns
  those. Run `python tools/generate.py sync` afterwards.
- Every claim traces to a source in front-matter. If a claim has no source,
  cut it.
- The **Common mistakes** section states the mistake, why it is dangerous,
  and the safer alternative — in that order.
- The **Real-world implementations** section names a production system and
  what it does differently.
```

- [ ] **Step 4: Write `prompts/freshness-auditor.md`**

```markdown
# Role: freshness auditor

Compare the existing page at **<PATH>** against the research findings below.

Produce:

- **Added** — guidance that now exists and the page lacks
- **Changed** — guidance the page states that current sources contradict
- **Deprecated** — guidance the page recommends that is no longer recommended

For each item, quote the page's current wording and the source that
supersedes it.

Then recommend one of:

- **Edit and re-review** — update the page, set `reviewed` to today
- **Write an ADR** — the change reverses a recorded decision, so
  `docs/decisions/` needs an entry before the page changes
- **No change** — the page is current; set `reviewed` to today

This role replaces a version-diff generator. The changelog comes from git;
this asks the question git cannot: is the page still true?
```

- [ ] **Step 5: Write `prompts/README.md`**

```markdown
# Authoring prompts

Four roles, run by hand, in this order for a new page:

1. `research-agent.md` — gather sources
2. `documentation-writer.md` — turn research into a page
3. `architecture-reviewer.md` — when checking an implementation, not a page
4. `freshness-auditor.md` — when a page enters the research queue

The research queue at `docs/research-queue.md` tells you which pages are due.
A page is due when its status is `stub`, or when `reviewed + review_interval`
has passed.

Promote a role to a Claude Code skill only after it has earned it across
several modules.
```

- [ ] **Step 6: Commit**

```bash
git add prompts
git commit -m "docs: add authoring prompt roles"
```

---

## What is deliberately not here

Per the spec: Outline synchronization, per-document version numbering as the
changelog spine, social cards, a comment system, multiple languages, search
analytics, and any generator output beyond the six blocks implemented above.
