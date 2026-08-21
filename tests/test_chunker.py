import json

import pytest

from rag_chunker.chunker import _Piece, _join_pieces, _tail_overlap, chunk_markdown, chunks_to_jsonl


def test_empty_document_has_no_chunks():
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n\n  ") == []


def test_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError):
        chunk_markdown("text", max_tokens=0)


def test_rejects_negative_overlap():
    with pytest.raises(ValueError):
        chunk_markdown("text", overlap=-1)


def test_rejects_overlap_not_smaller_than_max_tokens():
    with pytest.raises(ValueError):
        chunk_markdown("text", max_tokens=10, overlap=10)


def test_single_paragraph_with_no_heading():
    chunks = chunk_markdown("Just one short paragraph.", max_tokens=512, overlap=64)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.index == 0
    assert chunk.heading_path == []
    assert chunk.body == "Just one short paragraph."
    assert chunk.text == "Just one short paragraph."
    assert chunk.start_line == 1
    assert chunk.end_line == 1
    assert chunk.oversized is False


def test_heading_path_reflects_nesting():
    text = "# A\n\nIntro text.\n\n## B\n\nNested text.\n"
    chunks = chunk_markdown(text, max_tokens=512, overlap=32)
    assert [c.heading_path for c in chunks] == [["A"], ["A", "B"]]


def test_sibling_heading_resets_the_path():
    text = "# A\n\ntext one\n\n# C\n\ntext two\n"
    chunks = chunk_markdown(text, max_tokens=512, overlap=32)
    assert [c.heading_path for c in chunks] == [["A"], ["C"]]


def test_no_heading_prefix_option_omits_the_prefix_from_text():
    text = "# A\n\nSome body text.\n"
    chunks = chunk_markdown(text, max_tokens=512, overlap=32, heading_prefix=False)
    assert chunks[0].text == chunks[0].body
    assert "A" not in chunks[0].text


def test_oversized_code_block_is_emitted_whole_and_flagged():
    text = "# Doc\n\n```\nprint('hello world, this line is deliberately long')\n```\n"
    chunks = chunk_markdown(text, max_tokens=5, overlap=1)
    assert len(chunks) == 1
    assert chunks[0].oversized is True
    assert chunks[0].body.startswith("```")
    assert chunks[0].body.endswith("```")


def test_chunk_indices_are_sequential():
    text = "# A\n\none\n\n# B\n\ntwo\n\n# C\n\nthree\n"
    chunks = chunk_markdown(text, max_tokens=512, overlap=32)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_packing_and_overlap_across_two_chunks():
    text = "# Doc\n\nAlpha bravo charlie delta.\n\nEcho foxtrot golf hotel.\n"
    chunks = chunk_markdown(text, max_tokens=15, overlap=4)

    assert len(chunks) == 2

    first, second = chunks
    assert first.heading_path == ["Doc"]
    assert first.body == "Alpha bravo charlie delta."
    assert first.text == "Doc\n\nAlpha bravo charlie delta."
    assert first.start_line == 3
    assert first.end_line == 3
    assert first.token_estimate == 9
    assert first.oversized is False

    assert second.heading_path == ["Doc"]
    assert second.body == "charlie delta.\n\nEcho foxtrot golf hotel."
    assert second.text == "Doc\n\ncharlie delta.\n\nEcho foxtrot golf hotel."
    assert second.start_line == 5
    assert second.end_line == 5
    assert second.token_estimate == 13
    assert second.oversized is False


def test_chunks_to_jsonl_round_trips_through_json():
    chunks = chunk_markdown("# Doc\n\nSome text.\n", max_tokens=512, overlap=32)
    lines = chunks_to_jsonl(chunks).split("\n")
    assert len(lines) == len(chunks)
    for line, chunk in zip(lines, chunks):
        assert json.loads(line) == chunk.to_dict()


def test_chunks_to_jsonl_of_empty_list_is_empty_string():
    assert chunks_to_jsonl([]) == ""


def test_tail_overlap_returns_empty_for_non_positive_budget():
    assert _tail_overlap("alpha beta gamma", 0) == ""
    assert _tail_overlap("", 10) == ""


def test_tail_overlap_keeps_words_that_fit_from_the_end():
    # "gamma" alone costs 2 tokens; adding "beta" would push it to 3.
    assert _tail_overlap("alpha beta gamma", 2) == "gamma"


def test_tail_overlap_returns_whole_body_when_it_fits():
    assert _tail_overlap("one two", 100) == "one two"


def test_join_pieces_rejoins_same_block_fragments_with_their_separator():
    pieces = [
        _Piece("First sentence.", 1, 1, "block-a", None),
        _Piece("Second sentence.", 1, 1, "block-a", " "),
    ]
    assert _join_pieces(pieces) == "First sentence. Second sentence."


def test_join_pieces_separates_different_blocks_with_a_blank_line():
    pieces = [
        _Piece("Paragraph one.", 1, 1, "block-a", None),
        _Piece("Paragraph two.", 3, 3, "block-b", None),
    ]
    assert _join_pieces(pieces) == "Paragraph one.\n\nParagraph two."
