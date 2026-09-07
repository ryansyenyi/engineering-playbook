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
