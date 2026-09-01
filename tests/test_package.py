import re
from pathlib import Path

import rag_chunker

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version():
    # No tomllib on 3.9, and pulling in a TOML dependency for one field
    # would break the zero-dependency promise, so read it as text.
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', _PYPROJECT.read_text())
    assert match, "pyproject.toml has no top-level version field"
    return match.group(1)


def test_all_names_are_actually_importable_from_the_top_level():
    # Regression guard: this package once shipped an __init__.py that imported
    # a chunker module that did not exist, so `import rag_chunker` failed outright.
    for name in rag_chunker.__all__:
        assert hasattr(rag_chunker, name), "rag_chunker.__all__ lists %r but it is not importable" % name


def test_reexported_names_are_the_same_objects_as_the_submodules():
    from rag_chunker import chunker, markdown, sentences, tokens

    assert rag_chunker.chunk_markdown is chunker.chunk_markdown
    assert rag_chunker.chunks_to_jsonl is chunker.chunks_to_jsonl
    assert rag_chunker.Chunk is chunker.Chunk
    assert rag_chunker.DEFAULT_MAX_TOKENS is chunker.DEFAULT_MAX_TOKENS
    assert rag_chunker.DEFAULT_OVERLAP is chunker.DEFAULT_OVERLAP
    assert rag_chunker.parse_blocks is markdown.parse_blocks
    assert rag_chunker.Block is markdown.Block
    assert rag_chunker.split_sentences is sentences.split_sentences
    assert rag_chunker.estimate_tokens is tokens.estimate_tokens
    assert rag_chunker.fits_budget is tokens.fits_budget


def test_version_is_a_non_empty_string():
    assert isinstance(rag_chunker.__version__, str)
    assert rag_chunker.__version__


def test_version_matches_pyproject_toml():
    # These are two independent copies of the same fact; nothing else
    # catches it if a release bumps one and not the other.
    assert rag_chunker.__version__ == _pyproject_version()


def test_chunk_markdown_is_usable_from_the_package_root():
    chunks = rag_chunker.chunk_markdown("# Title\n\nBody text.\n")
    assert [chunk.heading_path for chunk in chunks] == [["Title"]]
