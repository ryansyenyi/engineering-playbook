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
