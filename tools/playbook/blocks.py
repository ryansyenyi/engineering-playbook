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
