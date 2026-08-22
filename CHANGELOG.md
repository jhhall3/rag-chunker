# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Markdown block parser (`rag_chunker.markdown`) that recognizes ATX headings,
  fenced code, pipe tables, list runs, and paragraphs.
- Character-class token estimator (`rag_chunker.tokens`) with no third-party
  dependency.
- Sentence splitter (`rag_chunker.sentences`) with an abbreviation guard for
  technical prose (`e.g.`, `Dr. Chen`, `v1.4`, numbered lists).
- Heading-aware chunk packer (`rag_chunker.chunker`): packs blocks into
  token-budgeted chunks that never span a heading, keeps code blocks and
  tables atomic (flagging them `oversized` rather than splitting them),
  prefixes each chunk with its heading path, and supports configurable
  overlap between consecutive chunks in a section.
- `rag-chunker` command-line entry point: reads a file or stdin, writes JSON
  Lines or an indented JSON array to stdout or a file, and can print a size
  summary to stderr with `--stats`.
- Test suite for the parser, sentence splitter, token estimator, chunker, and
  CLI.
