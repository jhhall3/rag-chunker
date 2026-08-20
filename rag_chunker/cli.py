"""Command-line entry point: read a markdown file, print chunks as JSON.

Kept thin on purpose -- argument parsing and I/O only. Anything that decides
how chunking works belongs in chunker.py so the library and the CLI can never
drift apart on behaviour.
"""

import argparse
import json
import sys

from .chunker import DEFAULT_MAX_TOKENS, DEFAULT_OVERLAP, chunk_markdown, chunks_to_jsonl

__all__ = ["main", "build_parser"]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rag-chunker",
        description="Split a markdown file into heading-aware, token-budgeted chunks.",
    )
    parser.add_argument("path", help="markdown file to chunk, or - to read stdin")
    parser.add_argument(
        "--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="chunk size ceiling (default: %(default)s)"
    )
    parser.add_argument(
        "--overlap", type=int, default=DEFAULT_OVERLAP, help="trailing tokens repeated into the next chunk (default: %(default)s)"
    )
    parser.add_argument(
        "--no-heading-prefix", action="store_true", help="do not prepend the heading path to chunk text"
    )
    parser.add_argument(
        "--array", action="store_true", help="emit one indented JSON array instead of JSON lines"
    )
    parser.add_argument("--stats", action="store_true", help="print a size summary to stderr")
    parser.add_argument("-o", "--output", metavar="PATH", help="write the result to a file instead of stdout")
    return parser


def _read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _render(chunks, as_array):
    if as_array:
        return json.dumps([chunk.to_dict() for chunk in chunks], indent=2, ensure_ascii=False)
    return chunks_to_jsonl(chunks)


def _print_stats(chunks, stream):
    if not chunks:
        stream.write("0 chunks\n")
        return
    tokens = [chunk.token_estimate for chunk in chunks]
    oversized = sum(1 for chunk in chunks if chunk.oversized)
    stream.write(
        "%d chunks | tokens min %d avg %d max %d | %d oversized\n"
        % (len(chunks), min(tokens), sum(tokens) // len(tokens), max(tokens), oversized)
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.path)
    except OSError as exc:
        parser.error("could not read %s: %s" % (args.path, exc.strerror or exc))

    try:
        chunks = chunk_markdown(
            text,
            max_tokens=args.max_tokens,
            overlap=args.overlap,
            heading_prefix=not args.no_heading_prefix,
        )
    except ValueError as exc:
        parser.error(str(exc))

    output = _render(chunks, args.array)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
            handle.write("\n")
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")

    if args.stats:
        _print_stats(chunks, sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
