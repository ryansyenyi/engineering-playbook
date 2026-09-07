"""Generate derived playbook content.

Two subcommands with different guarantees:

    sync   Writes blocks derived only from front-matter into committed
           sources. Deterministic, so `--check` can verify it in CI.
    build  Writes pages derived from git history and today's date. Those
           pages are gitignored build artifacts, never committed.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from playbook import blocks, frontmatter, gitmeta, pages as renderers


def _matrix_csv_path(root: Path, page: frontmatter.Page) -> Path:
    stem = Path(page.path).stem
    return root / "data" / "decisions" / f"{stem}.csv"


def _load_matrix_data(
    root: Path, parsed: list[frontmatter.Page]
) -> tuple[dict[str, list[list[str]]], list[frontmatter.Problem]]:
    """Read the CSV backing every matrix page (except matrices/index.md).

    Matrices are pure sync inputs, same as front-matter: deterministic,
    committed, and checked by `--check`. A missing CSV is collected as a
    Problem rather than raised, consistent with every other validation
    failure in this module.
    """
    data: dict[str, list[list[str]]] = {}
    problems: list[frontmatter.Problem] = []
    for page in parsed:
        if page.generated:
            continue
        if not page.path.startswith("matrices/") or page.path == "matrices/index.md":
            continue
        csv_path = _matrix_csv_path(root, page)
        if not csv_path.exists():
            relative = csv_path.relative_to(root).as_posix()
            problems.append(
                frontmatter.Problem(page.path, "matrix", f"expected CSV at {relative}")
            )
            continue
        with csv_path.open(newline="", encoding="utf-8") as handle:
            data[page.path] = [row for row in csv.reader(handle)]
    return data, problems


def sync_outputs(docs_dir: Path) -> tuple[dict[Path, str], list[frontmatter.Problem]]:
    parsed, problems = frontmatter.load_all(docs_dir)
    if problems:
        return {}, problems

    # docs_dir is always root / "docs" (see main()); derive root from it
    # rather than widening this function's signature just for matrix CSVs.
    root = docs_dir.parent
    matrix_data, matrix_problems = _load_matrix_data(root, parsed)
    if matrix_problems:
        return {}, matrix_problems

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
        if page.path in matrix_data:
            text = blocks.upsert_block(
                text, "matrix", renderers.render_matrix(matrix_data[page.path])
            )
        outputs[file] = text
    return outputs, []


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
