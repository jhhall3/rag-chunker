"""Pins the CLI transcripts quoted in the README against the real doc.md.

The README shows exact chunk records and stats lines produced by running the
CLI on doc.md. Nothing else catches it if a change to the chunker, the sample
document, or the README lets those three drift apart again.
"""

import json
from pathlib import Path

from rag_chunker.cli import main

_DOC = Path(__file__).resolve().parent.parent / "doc.md"

_CHUNK_0_TEXT = (
    "Vector index runbook\n\n"
    "This runbook covers the nightly reindex job and the checks that follow it."
)

_CHUNK_1_TEXT = (
    "Vector index runbook > Reindex\n\n"
    "Run the job from the scheduler, never from a laptop:\n\n"
    "```bash\n"
    "python -m pipeline.reindex \\\n"
    "  --source s3://docs/current \\\n"
    "  --max-tokens 512 \\\n"
    "  --overlap 64\n"
    "```\n\n"
    "The job reads every document under the source prefix, chunks it, and writes\n"
    "new vectors to a staging index. It does not touch the live index until the\n"
    "checks below pass."
)


def test_max_tokens_120_overlap_30_matches_the_readme_transcript(capsys):
    assert main([str(_DOC), "--max-tokens", "120", "--overlap", "30", "--stats"]) == 0

    captured = capsys.readouterr()
    lines = captured.out.rstrip("\n").split("\n")

    assert len(lines) == 5
    assert json.loads(lines[0]) == {
        "index": 0,
        "text": _CHUNK_0_TEXT,
        "heading_path": ["Vector index runbook"],
        "start_line": 3,
        "end_line": 3,
        "token_estimate": 23,
    }
    assert json.loads(lines[1]) == {
        "index": 1,
        "text": _CHUNK_1_TEXT,
        "heading_path": ["Vector index runbook", "Reindex"],
        "start_line": 7,
        "end_line": 18,
        "token_estimate": 100,
    }
    assert captured.err == "5 chunks | tokens min 23 avg 74 max 128 | 1 oversized\n"


def test_max_tokens_60_overlap_20_matches_the_readme_stats_line(capsys):
    assert main([str(_DOC), "--max-tokens", "60", "--overlap", "20", "--stats"]) == 0

    captured = capsys.readouterr()
    assert len(captured.out.rstrip("\n").split("\n")) == 8
    assert captured.err == "8 chunks | tokens min 23 avg 55 max 120 | 2 oversized\n"
