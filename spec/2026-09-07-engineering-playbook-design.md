# Engineering Playbook on Zensical — Design

**Date:** 2026-09-07
**Status:** Approved for implementation planning

## Purpose

Build a living software architecture playbook as a static site: architecture
patterns (what options exist), implementation standards (how to build them),
decision records (why one option was chosen), production checklists (how to
verify), and a continuously updated record of what changed.

Every module is a complete implementation guide, not a summary.

## Context and constraints

- **Personal project.** Standalone, generic content. No relationship to the
  PM Advisors Outline wiki, no PMA branding, no work-specific material.
- **Solo author** working with Claude as a research and drafting assistant.
- **Public GitHub Pages** deployment from a public repository.
- **Zensical** is the documentation platform, chosen deliberately. It is
  alpha software (0.0.x, pre-beta), so versions are pinned exactly.

### Platform capabilities confirmed

Verified against Zensical documentation on 2026-09-07:

| Capability | Status |
| --- | --- |
| Markdown, Python Markdown extensions | Supported |
| Mermaid diagrams via `pymdownx.superfences` custom fence | Supported |
| `search`, `tags`, `table-reader`, `section-index` plugins | Supported (`tags` since 0.0.58, `table-reader` since 0.0.41) |
| Instant navigation, prefetch, progress indicator | Supported |
| Instant page previews on link hover | Supported |
| Light/dark palette toggle | Supported |
| Grid cards | Supported |
| GitHub Pages deploy via GitHub Actions | Documented and supported |

### Platform gaps and their resolutions

| Gap | Resolution |
| --- | --- |
| No blog plugin | `changelog.md` is generated from git history, grouped by month |
| No `git-revision-date` plugin | Per-page "last updated" is generated into the page from `git log` |
| No build-time `hooks` support | Generation runs as a pre-build script that writes into markdown sources; output is committed |
| No `gh-deploy` command | Deploy via `upload-pages-artifact` / `deploy-pages` GitHub Actions |
| Alpha software | Exact version pin in `pyproject.toml`; CI never floats |

## Architecture

### Approach: front-matter and git as the database, CSV for curated data

Anything that is a byproduct of writing — recently updated, changelog,
research queue, ADR index, per-page last-updated — is **derived** from
front-matter and git history. It is never typed twice.

Anything that is genuinely curated data rather than a byproduct — the
engineering decision matrices — lives in `data/decisions/*.csv` and is
rendered by the `table-reader` plugin. These matrices are the playbook's most
reusable asset and deserve a structured, machine-readable home.

The raw concept called for a hand-maintained changelog database. In a git
repository that is a duplicate of history, so it is generated instead.

### Repository layout

```
engineering_playbook/
├─ zensical.toml
├─ pyproject.toml
├─ Makefile
├─ .github/workflows/docs.yml
├─ spec/                      # design documents (NOT published)
├─ tools/
│  ├─ generate.py
│  ├─ playbook/
│  │  ├─ frontmatter.py
│  │  ├─ gitmeta.py
│  │  ├─ blocks.py
│  │  └─ pages.py
│  └─ templates/
│     ├─ module.md
│     ├─ subpage.md
│     ├─ adr.md
│     ├─ checklist.md
│     └─ matrix.md
├─ data/decisions/*.csv
├─ prompts/
│  ├─ research-agent.md
│  ├─ architecture-reviewer.md
│  ├─ documentation-writer.md
│  └─ freshness-auditor.md
└─ docs/
   ├─ index.md               # dashboard
   ├─ recently-updated.md    # generated
   ├─ changelog.md           # generated
   ├─ research-queue.md      # generated
   ├─ principles/
   ├─ modules/
   │  ├─ index.md
   │  ├─ authentication/     # v1 deep module
   │  ├─ authorization/
   │  ├─ multi-tenancy/
   │  ├─ api-design/
   │  ├─ database-design/
   │  ├─ networking/
   │  └─ observability/
   ├─ security/
   ├─ decisions/
   ├─ checklists/
   ├─ matrices/
   └─ stylesheets/extra.css
```

`spec/` sits at the repository root rather than under `docs/` because `docs/`
is the site content root; a spec placed there would be published as a
playbook page.

### Information architecture decisions

**Security is one section, not two.** The source concept lists Security both
as a core module and as a separate security wiki, with roughly 80% overlap.
The playbook has a single home for security content at `docs/security/`.
`docs/modules/` links to it and does not duplicate it.

**Principles are pages, not a bullet list.** Nine principles (security-first,
API-first, cloud-native, twelve-factor, multi-tenant design, least privilege,
defense in depth, event-driven architecture, domain-driven design) each get a
page so module pages can link to them and Zensical's instant preview can show
the definition on hover.

**Matrices are top-level.** Some matrices belong to a module (JWT vs session
cookies) and some belong to none (monolith vs microservices). They live in
`docs/matrices/`, cross-referenced to modules by tag.

**Depth is capped at three levels** (`modules/authentication/jwt.md`).

## The page contract

Every page carries front-matter:

```yaml
---
title: JWT
module: authentication      # taxonomy key; groups generated pages
status: reviewed            # stub | draft | reviewed
version: 1.2                # optional; for citing a specific revision
reviewed: 2026-09-07        # last human review, not file mtime
review_interval: 180        # days until the page re-enters the research queue
tags: [Authentication, Tokens]
sources:
  - { type: standard, name: "OWASP JWT Cheat Sheet", url: "https://..." }
  - { type: rfc,      name: "RFC 7519",              url: "https://..." }
---
```

Required fields: `title`, `module`, `status`, `tags`. Pages with
`status: reviewed` additionally require `reviewed`.

`status`, `reviewed`, and `review_interval` make the research queue
self-populating: a page is queued if its status is `stub`, or if
`reviewed + review_interval` is in the past. This targets the real failure
mode of a playbook — not missing pages, but confidently stale ones.

Document version numbers are not the spine of the changelog. Git history is.
The `version` field exists for citation only.

### Generated blocks

The generator writes into markdown sources between sentinel markers, and the
output is committed:

```markdown
<!-- generated:references start -->
| Type | Source |
| ---- | ------ |
| Standard | [OWASP JWT Cheat Sheet](https://...) |
| RFC | [RFC 7519](https://...) |
<!-- generated:references end -->
```

Block names: `references`, `page-footer`, `recently-updated`, `changelog`,
`research-queue`, `adr-index`.

Generating into committed sources rather than at build time means generated
content is reviewable in `git diff` before it ships, the site builds with
plain `zensical build` and no custom runtime, and the markdown remains
complete and portable if the platform ever changes.

## Page templates

`tools/templates/` holds one template per page kind.

**`module.md`** — executive summary (purpose, when to use, when *not* to use),
architecture overview with mermaid diagrams, flow diagram, functional
requirements, non-functional requirements, pros and cons, alternatives,
security considerations, implementation examples, common mistakes, real-world
implementations, references.

**`subpage.md`** — the same structure minus the requirements sections.

**`adr.md`** — context, decision, status, consequences, alternatives
considered, references.

**`checklist.md`** — verification items mapped to OWASP guidance where
applicable, so the baseline is industry-standard rather than opinion-based.

**`matrix.md`** — a page that embeds a `data/decisions/*.csv` table via
`table-reader`, followed by the reasoning: why, tradeoffs, migration path.

## The generator

### Units

| Unit | Responsibility |
| --- | --- |
| `frontmatter.py` | Parse a markdown file into a `Page` dataclass; validate fields |
| `gitmeta.py` | One `git log` invocation for the whole tree; return commits per path |
| `blocks.py` | Pure functions to find and replace sentinel blocks in text |
| `pages.py` | Renderers, one pure function per generated output |
| `generate.py` | CLI entry point: walk, orchestrate, write or `--check` |

`gitmeta` runs a single subprocess for the entire tree rather than one per
file, because the per-file approach degrades badly past a hundred pages.

### Data flow

1. Walk `docs/**/*.md`, parse front-matter into `list[Page]`, collecting
   validation errors.
2. Query git history once for all documented paths.
3. Run renderers to produce block bodies.
4. Replace sentinel blocks in the markdown sources on disk.

### Renderers

- `recently_updated(pages, history)` — most recently changed pages, limit 10
- `changelog(history)` — commits grouped by month, linked to their pages
- `research_queue(pages, today)` — stubs plus pages past their review interval
- `adr_index(pages)` — every ADR with status and date
- `references(page)` — the sources table
- `page_footer(page, history)` — last updated, status, review due

### Error handling

- **Validation errors are collected, not raised.** One run reports every bad
  page as `path: field: problem`, exits non-zero, and writes nothing. Partial
  writes are never performed.
- **A page missing its sentinel block gets the block appended** rather than
  failing, so hand-written pages work without being template-derived.
- **No git repository or no commits** yields empty history; renderers emit a
  "no history yet" placeholder rather than crashing. Day one must work.
- **`--check` mode** computes output in memory, diffs against disk, names
  every stale file, exits non-zero, and writes nothing.

### Idempotency

Running the generator twice must produce byte-identical files. This property
is what makes `--check` trustworthy in CI and keeps generated blocks out of
diff noise. It is tested explicitly.

### Testing

Tests are written before implementation.

- `blocks` — table-driven pure tests: markers absent, markers present,
  replace-twice-is-identical.
- `frontmatter` — valid page, missing required field, malformed date, unknown
  `status` value.
- `pages` — fixture `Page` lists to expected markdown, including the empty
  input case for every renderer.
- `gitmeta` — a real temporary git repository fixture with two commits;
  integration rather than a mocked subprocess.
- End-to-end — fixture `docs/` tree: run once and assert content, run again
  and assert zero diff, run `--check` and assert a zero exit code.

## Zensical configuration

```toml
[project]
site_name        = "Engineering Playbook"
site_url         = "https://<user>.github.io/engineering-playbook/"
site_description = "Living architecture playbook: patterns, standards, decisions, checklists."
repo_url         = "https://github.com/<user>/engineering-playbook"
repo_name        = "<user>/engineering-playbook"
edit_uri         = "edit/main/docs/"
docs_dir         = "docs"
site_dir         = "site"
extra_css        = ["stylesheets/extra.css"]
watch            = ["data", "tools"]

# nav is explicit and enumerates every page, mirroring the repository
# layout above in this order: Playbook (index.md), Principles, Modules,
# Security, Decisions, Checklists, Matrices, Changelog.
nav = [
  { "Playbook" = "index.md" },
  { "Principles" = [ "principles/index.md", "..." ] },
  { "Modules" = [ "modules/index.md",
                  { "Authentication" = [ "modules/authentication/index.md", "..." ] } ] },
  { "Security" = [ "security/index.md", "..." ] },
  { "Decisions" = [ "decisions/index.md", "..." ] },
  { "Checklists" = [ "checklists/index.md", "..." ] },
  { "Matrices" = [ "matrices/index.md", "..." ] },
  { "Changelog" = "changelog.md" },
]

[project.theme]
variant = "modern"
features = [
  "navigation.instant", "navigation.instant.prefetch", "navigation.instant.progress",
  "navigation.sections", "navigation.top", "toc.follow",
  "search.highlight", "search.suggest",
  "content.code.copy", "content.action.edit",
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

[project.markdown_extensions]
pymdownx.superfences.custom_fences = [
  { name = "mermaid", class = "mermaid", format = "pymdownx.superfences.fence_code_format" },
]
```

Notes:

- **Version floor `zensical >= 0.0.58`**, pinned exactly in `pyproject.toml`.
- **`variant = "modern"`**; `classic` exists to preserve the appearance of
  migrated Material for MkDocs projects, which does not apply here.
- **`section-index`** makes each module's `index.md` the clickable section
  header, so selecting "Authentication" opens the overview.
- **Feature list requires a smoke build.** `navigation.instant*`,
  `search.highlight`, `content.action.edit`, the palette configuration, and
  the mermaid fence are confirmed in Zensical's documentation.
  `navigation.sections`, `navigation.top`, `toc.follow`, `search.suggest`,
  and `content.code.copy` come from the Material for MkDocs feature surface
  that Zensical states it supports in full but does not enumerate
  individually. The first implementation step confirms each one against a
  real build; any that fail are removed from the list rather than worked
  around.

## Authoring workflow

The dashboard (`docs/index.md`) presents grid cards for the six areas,
followed by generated recently-updated and research-queue blocks.

Four Claude roles live in `prompts/` as plain markdown files, run by hand:

1. **`research-agent.md`** — gather authoritative guidance on a topic from
   OWASP, RFCs, and vendor documentation; output findings, citations, and
   what has changed.
2. **`architecture-reviewer.md`** — compare an implementation against the
   module's guidance; output gaps, risks, and improvements.
3. **`documentation-writer.md`** — convert research output into the page
   template, front-matter included.
4. **`freshness-auditor.md`** — compare an existing page against freshly
   gathered sources; report added, changed, and deprecated guidance. This
   replaces the source concept's "diff generator," whose changelog role is
   now filled by git. Its output moves a page back to `reviewed` or produces
   an ADR.

Promoting any of these to a Claude Code skill is a later, separate decision,
made only after a role has proven itself across several modules.

### Make targets

`install` · `gen` · `check` (pytest and `generate --check`) · `serve` ·
`build` · `page KIND=module PATH=modules/authorization/index.md`

### CI

On push to `main`: set up Python, install pinned dependencies, run
`make check`, run `zensical build --clean`, upload the pages artifact, and
deploy. The build fails if generated content is stale or tests fail.

## Prerequisites

- `git init` in the project directory. The generator reads git history, so
  this is load-bearing rather than housekeeping.
- Python with `pip` or `uv` available.

## Scope of v1

Complete when:

- The site builds locally and deploys to GitHub Pages.
- The Authentication module is complete: overview plus ten subpages
  (email and password, magic link, passkeys, social login, enterprise SSO,
  OIDC, OAuth2, JWT, session cookies, refresh tokens), with mermaid flow
  diagrams for login, password reset, and refresh token flows.
- One authentication checklist, two decision matrices (password hashing;
  JWT versus session cookies), and one ADR exist.
- The remaining seven modules exist as stubs with valid front-matter.
- The security section is indexed with its fifteen pages stubbed.
- The generator passes its tests and runs in CI.
- Templates and prompt files are in place.

### Explicitly out of scope for v1

Outline synchronization; per-document version numbering as the changelog
spine; social cards; a comment system; multiple languages; search analytics;
any generator output beyond the six blocks named above.

## Roadmap beyond v1

Following the source concept's prioritization by reuse frequency:

- **Phase 2 — Identity foundation:** Authorization, Multi-tenancy, Session
  Management, Password Security brought to full depth.
- **Phase 3 — Application architecture:** API Design, Database Design,
  Caching, Event-driven Architecture, File Storage.
- **Phase 4 — Production engineering:** Logging, Monitoring, Deployment,
  Backup, Incident Response.

Each phase is planned and executed separately.
