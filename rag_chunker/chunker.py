"""Heading-aware packing of markdown blocks into token-budgeted chunks.

The block parser already knows what must never be torn apart -- a heading, a
fenced code block, a table. This module is the packing policy on top of that:
walk the blocks in order, keep a running heading path, and fill chunks up to
``max_tokens`` without ever letting one span a heading. Atomic blocks that do
not fit are emitted whole and flagged ``oversized`` rather than mangled.
Everything else that overflows a chunk on its own (an oversized paragraph or
list) falls back to the smallest unit that still means something: sentences
for prose, lines for list items.
"""

import collections
import json

from .markdown import parse_blocks
from .sentences import split_sentences
from .tokens import estimate_tokens

__all__ = ["Chunk", "DEFAULT_MAX_TOKENS", "DEFAULT_OVERLAP", "chunk_markdown", "chunks_to_jsonl"]

DEFAULT_MAX_TOKENS = 512
DEFAULT_OVERLAP = 64

# A packing unit smaller than a whole block: either a whole block (sep=None,
# group=id(block)) or a fragment of one (a sentence or a list line), tagged
# with the block it came from so adjacent fragments of the same block are
# rejoined with `sep` instead of the blank line used between blocks.
_Piece = collections.namedtuple("_Piece", "text start_line end_line group sep")


class Chunk(object):
    """One packed, embeddable slice of a document."""

    __slots__ = ("index", "text", "body", "heading_path", "start_line", "end_line", "token_estimate", "oversized")

    def __init__(self, text, body, heading_path, start_line, end_line, token_estimate, oversized, index=0):
        self.index = index
        self.text = text
        self.body = body
        self.heading_path = heading_path
        self.start_line = start_line
        self.end_line = end_line
        self.token_estimate = token_estimate
        self.oversized = oversized

    def to_dict(self):
        """The JSONL record for this chunk."""
        return {
            "index": self.index,
            "text": self.text,
            "heading_path": list(self.heading_path),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_estimate": self.token_estimate,
        }

    def __repr__(self):
        return "Chunk(index=%d, heading_path=%r, lines=%d-%d, tokens=%d%s)" % (
            self.index,
            self.heading_path,
            self.start_line,
            self.end_line,
            self.token_estimate,
            ", oversized" if self.oversized else "",
        )


def chunk_markdown(text, max_tokens=DEFAULT_MAX_TOKENS, overlap=DEFAULT_OVERLAP, heading_prefix=True):
    """Split ``text`` into :class:`Chunk` objects that respect its structure."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")

    blocks = parse_blocks(text)
    chunks = []
    heading_stack = []  # list of (level, title), innermost last
    section = []  # non-heading blocks under the current heading path

    def current_path():
        return [title for _, title in heading_stack]

    for block in blocks:
        if block.kind == "heading":
            if section:
                chunks.extend(_pack_section(section, current_path(), max_tokens, overlap, heading_prefix))
                section = []
            while heading_stack and heading_stack[-1][0] >= block.level:
                heading_stack.pop()
            heading_stack.append((block.level, block.title))
        else:
            section.append(block)

    if section:
        chunks.extend(_pack_section(section, current_path(), max_tokens, overlap, heading_prefix))

    for i, chunk in enumerate(chunks):
        chunk.index = i
    return chunks


def chunks_to_jsonl(chunks):
    """Serialise ``chunks`` as newline-delimited JSON."""
    return "\n".join(json.dumps(chunk.to_dict(), ensure_ascii=False) for chunk in chunks)


def _pack_section(blocks, heading_path, max_tokens, overlap, heading_prefix):
    prefix = " > ".join(heading_path) if heading_prefix and heading_path else ""
    prefix_cost = estimate_tokens(prefix + "\n\n") if prefix else 0
    body_budget = max(1, max_tokens - prefix_cost)

    pieces = _flatten_pieces(blocks, body_budget)
    if not pieces:
        return []

    chunks = []
    prev_body = ""
    i, n = 0, len(pieces)

    while i < n:
        overlap_text = _tail_overlap(prev_body, overlap) if chunks else ""
        if overlap_text:
            remaining_budget = max(1, body_budget - estimate_tokens(overlap_text) - estimate_tokens("\n\n"))
        else:
            remaining_budget = body_budget

        parts = [pieces[i]]
        j = i + 1
        while j < n:
            trial = parts + [pieces[j]]
            if estimate_tokens(_join_pieces(trial)) > remaining_budget:
                break
            parts = trial
            j += 1

        body = _join_pieces(parts)
        full_body = overlap_text + "\n\n" + body if overlap_text else body
        text = prefix + "\n\n" + full_body if prefix else full_body
        token_estimate = estimate_tokens(text)

        chunks.append(
            Chunk(
                text=text,
                body=full_body,
                heading_path=list(heading_path),
                start_line=min(p.start_line for p in parts),
                end_line=max(p.end_line for p in parts),
                token_estimate=token_estimate,
                oversized=token_estimate > max_tokens,
            )
        )
        prev_body = body
        i = j

    return chunks


def _flatten_pieces(blocks, body_budget):
    """Break each block into one or more :class:`_Piece`, splitting only what overflows alone."""
    pieces = []
    for block in blocks:
        if block.is_atomic or block.tokens <= body_budget:
            pieces.append(_Piece(block.text, block.start_line, block.end_line, id(block), None))
            continue

        if block.kind == "paragraph":
            sentences = split_sentences(block.text)
            if len(sentences) <= 1:
                pieces.append(_Piece(block.text, block.start_line, block.end_line, id(block), None))
                continue
            for sentence, start_line, end_line in _locate_sentences(block, sentences):
                pieces.append(_Piece(sentence, start_line, end_line, id(block), " "))
        else:  # kind == "list"
            line_no = block.start_line
            for line in block.text.split("\n"):
                if line.strip():
                    pieces.append(_Piece(line, line_no, line_no, id(block), "\n"))
                line_no += 1

    return pieces


def _locate_sentences(block, sentences):
    """Pair each sentence with the source line range it came from."""
    located = []
    cursor = 0
    for sentence in sentences:
        start = block.text.index(sentence, cursor)
        end = start + len(sentence)
        located.append(
            (
                sentence,
                block.start_line + block.text.count("\n", 0, start),
                block.start_line + block.text.count("\n", 0, end),
            )
        )
        cursor = end
    return located


def _join_pieces(parts):
    """Rebuild text from pieces: same-block fragments rejoin with their `sep`, blocks join with a blank line."""
    merged = []
    for piece in parts:
        if merged and merged[-1][1] == piece.group and piece.sep is not None:
            merged[-1][0] += piece.sep + piece.text
        else:
            merged.append([piece.text, piece.group])
    return "\n\n".join(text for text, _ in merged)


def _tail_overlap(body, budget):
    """The longest word-boundary suffix of `body` that fits in `budget` tokens."""
    if budget <= 0 or not body:
        return ""
    words = body.split()
    tail = []
    for word in reversed(words):
        candidate = [word] + tail
        if estimate_tokens(" ".join(candidate)) > budget:
            break
        tail = candidate
    return " ".join(tail)
