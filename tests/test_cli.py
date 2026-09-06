import io
import json
import sys

import pytest

import rag_chunker
from rag_chunker.cli import DEFAULT_MAX_TOKENS, DEFAULT_OVERLAP, build_parser, main


def test_version_flag_prints_version_and_exits_without_requiring_a_path(capsys):
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == "rag-chunker %s\n" % rag_chunker.__version__


def test_build_parser_defaults():
    args = build_parser().parse_args(["doc.md"])
    assert args.path == "doc.md"
    assert args.max_tokens == DEFAULT_MAX_TOKENS
    assert args.overlap == DEFAULT_OVERLAP
    assert args.no_heading_prefix is False
    assert args.array is False
    assert args.stats is False
    assert args.output is None


def test_main_reads_file_and_writes_jsonl_to_stdout(tmp_path, capsys):
    path = tmp_path / "doc.md"
    path.write_text("# Doc\n\nSome text.\n")

    assert main([str(path)]) == 0

    out = capsys.readouterr().out
    record = json.loads(out.strip())
    assert record["heading_path"] == ["Doc"]
    assert record["text"] == "Doc\n\nSome text."


def test_main_reads_from_stdin_when_path_is_a_dash(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("# Doc\n\nSome text.\n"))

    assert main(["-"]) == 0

    record = json.loads(capsys.readouterr().out.strip())
    assert record["heading_path"] == ["Doc"]


def test_main_array_option_emits_one_indented_json_array(tmp_path, capsys):
    path = tmp_path / "doc.md"
    path.write_text("# A\n\none\n\n# B\n\ntwo\n")

    main([str(path), "--array"])

    records = json.loads(capsys.readouterr().out)
    assert [record["heading_path"] for record in records] == [["A"], ["B"]]


def test_main_no_heading_prefix_option_omits_the_prefix(tmp_path, capsys):
    path = tmp_path / "doc.md"
    path.write_text("# Doc\n\nSome text.\n")

    main([str(path), "--no-heading-prefix"])

    record = json.loads(capsys.readouterr().out.strip())
    assert record["text"] == "Some text."


def test_main_writes_output_to_a_file_when_dash_o_is_given(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n\nSome text.\n")
    dest = tmp_path / "out.jsonl"

    assert main([str(src), "-o", str(dest)]) == 0

    record = json.loads(dest.read_text().strip())
    assert record["heading_path"] == ["Doc"]


def test_main_stats_option_prints_a_summary_to_stderr(tmp_path, capsys):
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n\nAlpha bravo charlie delta.\n\nEcho foxtrot golf hotel.\n")

    main([str(src), "--max-tokens", "15", "--overlap", "4", "--stats"])

    captured = capsys.readouterr()
    assert captured.err == "2 chunks | tokens min 9 avg 11 max 13 | 0 oversized\n"


def test_main_stats_for_an_empty_document_prints_zero_chunks(tmp_path, capsys):
    src = tmp_path / "empty.md"
    src.write_text("   \n\n  ")

    main([str(src), "--stats"])

    captured = capsys.readouterr()
    assert captured.out == "\n"
    assert captured.err == "0 chunks\n"


def test_main_reports_a_missing_file_as_a_parser_error(tmp_path, capsys):
    missing = tmp_path / "missing.md"

    with pytest.raises(SystemExit) as exc_info:
        main([str(missing)])

    assert exc_info.value.code == 2
    assert "could not read" in capsys.readouterr().err


def test_main_reports_invalid_overlap_as_a_parser_error(tmp_path, capsys):
    src = tmp_path / "doc.md"
    src.write_text("# Doc\n\nSome text.\n")

    with pytest.raises(SystemExit) as exc_info:
        main([str(src), "--max-tokens", "10", "--overlap", "10"])

    assert exc_info.value.code == 2
    assert "overlap must be smaller than max_tokens" in capsys.readouterr().err
