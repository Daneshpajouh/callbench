import logging
import re
from pathlib import Path

import pytest
from logsetup import log_failures, read_tsv, rule_logger
from smk_stub import DATA, Wildcards, make_smk

LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} (?P<level>[A-Z]+) rule=(?P<rule>\S+) "
    r"sample=(?P<sample>\S+) (?P<msg>.*)$"
)


def _lines(path: Path) -> list[re.Match[str]]:
    out = []
    for text in path.read_text().splitlines():
        match = LINE.match(text)
        assert match, text
        out.append(match)
    return out


def test_rule_logger_writes_rule_and_sample(tmp_path: Path) -> None:
    smk = make_smk(tmp_path, "vcfeval", wildcards=Wildcards(sample="HG002", caller="bcftools"))
    rule_logger(smk).info("read %d records", 3)
    (line,) = _lines(tmp_path / "vcfeval.log")
    assert (line["level"], line["rule"], line["sample"], line["msg"]) == (
        "INFO",
        "vcfeval",
        "HG002",
        "read 3 records",
    )


def test_rule_logger_uses_a_dash_without_a_sample_wildcard(tmp_path: Path) -> None:
    rule_logger(make_smk(tmp_path, "plots")).info("x")
    assert _lines(tmp_path / "plots.log")[0]["sample"] == "-"


def test_rule_logger_appends_to_an_existing_log(tmp_path: Path) -> None:
    log = tmp_path / "plots.log"
    log.write_text("shell output from an earlier step\n")
    rule_logger(make_smk(tmp_path, "plots")).info("second")
    text = log.read_text().splitlines()
    assert text[0] == "shell output from an earlier step"
    assert text[1].endswith("second")


def test_rule_logger_called_twice_does_not_duplicate_lines(tmp_path: Path) -> None:
    smk = make_smk(tmp_path, "plots")
    rule_logger(smk)
    rule_logger(smk).info("once")
    assert len(_lines(tmp_path / "plots.log")) == 1


@pytest.mark.parametrize(
    ("config", "debug_kept", "info_kept"),
    [
        pytest.param({}, False, True, id="default-is-info"),
        pytest.param({"log_level": "INFO"}, False, True, id="info"),
        pytest.param({"log_level": "debug"}, True, True, id="lower-case-debug"),
        pytest.param({"log_level": "WARNING"}, False, False, id="warning"),
    ],
)
def test_rule_logger_level_comes_from_config(
    tmp_path: Path, config: dict[str, str], debug_kept: bool, info_kept: bool
) -> None:
    log = rule_logger(make_smk(tmp_path, "plots", config=config))
    log.debug("d")
    log.info("i")
    log.warning("w")
    levels = [m["level"] for m in _lines(tmp_path / "plots.log")]
    assert ("DEBUG" in levels, "INFO" in levels, "WARNING" in levels) == (
        debug_kept,
        info_kept,
        True,
    )


def test_rule_logger_rejects_an_unknown_level(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="log_level must be one of"):
        rule_logger(make_smk(tmp_path, "plots", config={"log_level": "LOUD"}))


def test_rule_logger_does_not_reach_the_root_logger(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    rule_logger(make_smk(tmp_path, "plots")).info("quiet")
    assert caplog.records == []


def test_log_failures_logs_at_error_level_and_reraises(tmp_path: Path) -> None:
    log = rule_logger(make_smk(tmp_path, "plots"))
    with pytest.raises(ValueError, match="bad input"), log_failures(log):
        raise ValueError("bad input")
    (line,) = _lines(tmp_path / "plots.log")
    assert (line["level"], line["msg"]) == ("ERROR", "ValueError: bad input")


def test_log_failures_is_silent_without_an_error(tmp_path: Path) -> None:
    log = rule_logger(make_smk(tmp_path, "plots"))
    with log_failures(log):
        pass
    assert (tmp_path / "plots.log").read_text() == ""


def test_log_failures_leaves_base_exceptions_alone(tmp_path: Path) -> None:
    log = rule_logger(make_smk(tmp_path, "plots"))
    with pytest.raises(KeyboardInterrupt), log_failures(log):
        raise KeyboardInterrupt
    assert (tmp_path / "plots.log").read_text() == ""


def test_read_tsv_reads_a_table_and_can_keep_strings() -> None:
    assert list(read_tsv(DATA / "accuracy_expected.tsv").columns)[:3] == [
        "sample",
        "caller",
        "stratum",
    ]
    assert read_tsv(DATA / "accuracy_expected.tsv", as_str=True)["tp_base"].iloc[0] == "90"


def test_read_tsv_reports_an_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.tsv"
    empty.write_text("")
    with pytest.raises(ValueError, match=rf"{re.escape(str(empty))}: empty file"):
        read_tsv(empty)


def test_read_tsv_reports_a_malformed_table_with_its_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tsv"
    bad.write_text("a\tb\n1\t2\n3\t4\t5\t6\n")
    with pytest.raises(ValueError, match=rf"{re.escape(str(bad))}: malformed TSV.*line 3"):
        read_tsv(bad)


def test_logger_is_separate_per_rule(tmp_path: Path) -> None:
    a = rule_logger(make_smk(tmp_path, "plots"))
    b = rule_logger(make_smk(tmp_path, "profiling_table"))
    assert a is not b
    assert isinstance(a, logging.Logger)
