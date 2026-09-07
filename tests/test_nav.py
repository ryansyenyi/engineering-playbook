"""Nav entries must resolve to real files under docs/.

Zensical's `invalid_links` validation covers markdown links, not nav
structure: a nav entry pointing at a file that does not exist builds clean
and silently renders a dead nav item (confirmed against zensical 0.0.59).
This test is the safety net that catches that case instead.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import generate

ROOT = Path(__file__).resolve().parents[1]


def _walk_nav(nav: list) -> list[str]:
    """Recursively collect leaf path/URL strings from a nav structure.

    Entries are either a bare string, or a single-key table whose value is
    a string or a further list of entries.
    """
    entries: list[str] = []
    for item in nav:
        if isinstance(item, str):
            entries.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    entries.append(value)
                elif isinstance(value, list):
                    entries.extend(_walk_nav(value))
                else:
                    raise TypeError(f"unexpected nav value: {value!r}")
        else:
            raise TypeError(f"unexpected nav entry: {item!r}")
    return entries


def _load_nav_entries() -> list[str]:
    config = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))
    nav = config["project"]["nav"]
    return _walk_nav(nav)


def test_nav_entries_resolve_to_files():
    entries = _load_nav_entries()
    generated_pages = set(generate.GENERATED_PAGES)
    missing = []
    for entry in entries:
        if entry.startswith("http://") or entry.startswith("https://"):
            continue
        if entry in generated_pages:
            # Gitignored build artifacts; may not exist when tests run.
            continue
        if not (ROOT / "docs" / entry).exists():
            missing.append(entry)
    assert not missing, f"nav entries with no backing file under docs/: {missing}"


def test_nav_walk_finds_a_meaningful_number_of_entries():
    entries = _load_nav_entries()
    # Guards against a walker bug that silently returns an empty/tiny list,
    # which would make the resolution test above pass vacuously.
    assert len(entries) >= 40
