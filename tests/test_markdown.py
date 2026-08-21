from rag_chunker.markdown import parse_blocks
from rag_chunker.tokens import estimate_tokens


def test_blank_text_has_no_blocks():
    assert parse_blocks("") == []
    assert parse_blocks("   \n\n  ") == []


def test_heading_levels_and_titles():
    blocks = parse_blocks("# Title\n\n## Subtitle\n")
    assert [b.kind for b in blocks] == ["heading", "heading"]
    assert [b.level for b in blocks] == [1, 2]
    assert [b.title for b in blocks] == ["Title", "Subtitle"]


def test_heading_requires_space_after_hashes():
    blocks = parse_blocks("#NotAHeading\n")
    assert blocks[0].kind == "paragraph"


def test_paragraph_after_heading_has_correct_lines():
    blocks = parse_blocks("# Title\n\nSome text.\n")
    assert blocks[1].kind == "paragraph"
    assert blocks[1].text == "Some text."
    assert blocks[1].start_line == 3
    assert blocks[1].end_line == 3


def test_fenced_code_block_is_atomic_and_keeps_its_fences():
    text = "```python\nprint(1)\n```\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].kind == "code"
    assert blocks[0].is_atomic is True
    assert blocks[0].text == "```python\nprint(1)\n```"
    assert blocks[0].start_line == 1
    assert blocks[0].end_line == 3


def test_unterminated_fence_runs_to_end_of_document():
    text = "```\nno closing fence here\nmore text"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].kind == "code"
    assert blocks[0].end_line == 3


def test_pipe_table_is_atomic():
    text = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].kind == "table"
    assert blocks[0].is_atomic is True
    assert blocks[0].start_line == 1
    assert blocks[0].end_line == 3


def test_list_block_groups_consecutive_bullet_lines():
    text = "- one\n- two\n- three\n"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].kind == "list"
    assert blocks[0].is_atomic is False
    assert blocks[0].text == "- one\n- two\n- three"


def test_ordered_list_is_recognised_as_list():
    text = "1. one\n2. two\n"
    blocks = parse_blocks(text)
    assert blocks[0].kind == "list"


def test_paragraph_stops_before_a_following_heading():
    text = "Some prose.\n# Heading\n"
    blocks = parse_blocks(text)
    assert [b.kind for b in blocks] == ["paragraph", "heading"]
    assert blocks[0].text == "Some prose."


def test_block_tokens_matches_estimate_tokens():
    blocks = parse_blocks("# Title\n\nA short paragraph.\n")
    for block in blocks:
        assert block.tokens == estimate_tokens(block.text)


def test_setext_style_underline_is_read_as_a_paragraph():
    text = "Title\n=====\n"
    blocks = parse_blocks(text)
    assert blocks[0].kind == "paragraph"
