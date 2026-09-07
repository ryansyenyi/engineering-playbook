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
