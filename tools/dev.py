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
