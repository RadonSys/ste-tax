"""Naive rate on fixtures; checker report parsing; one live checker
call when a SKILLs checkout is present."""

import os
import shutil
from pathlib import Path

import pytest

from eval.compliance import (
    CheckerCli,
    default_trie,
    naive_compliance,
    parse_report,
    plurals,
)
from eval.records import Checked, Skipped


@pytest.mark.parametrize(
    ("text", "terms", "rate", "flagged"),
    [
        ("Remove the pump.", (), 2 / 3, ("PUMP",)),
        ("Remove the pump.", ("pump",), 1.0, ()),
        ("Make sure that the valve is closed.", ("valve",), 1.0, ()),
        # numbers leave the denominator; a term passes in its plural
        ("Remove 4 bolts.", ("bolt",), 1.0, ()),
        ("Clean the batteries.", ("BATTERY",), 1.0, ()),
        # a multi-word term counts whole, plural on its last word
        ("Remove the inner tubes.", ("INNER TUBE",), 1.0, ()),
        ("Remove the oil filter.", ("OIL FILTER",), 1.0, ()),
        ("Remove the tube.", ("INNER TUBE",), 2 / 3, ("TUBE",)),
        ("Answer: 200", (), 0.0, ("ANSWER",)),
        # nothing scorable: None, never a vacuous 1.0
        ("Answer: 200", ("Answer",), None, ()),
        ("200 45", (), None, ()),
        ("", (), None, ()),
    ],
)
def test_naive_compliance(text, terms, rate, flagged):
    got_rate, got_flagged = naive_compliance(text, terms, default_trie())
    assert got_flagged == flagged
    assert got_rate == (None if rate is None else pytest.approx(rate))


def test_plurals():
    assert plurals("TIRE") == ("TIRES", "TIREES")
    assert "BATTERIES" in plurals("BATTERY")
    assert "KEIES" not in plurals("KEY")


REPORT = {
    "version": "v0.1.1",
    "mode": "description",
    "ok": False,
    "summary": {"findings": {"punctuation": 1, "not_approved": 2}},
    "findings": [
        {"rule": "8.1", "kind": "punctuation", "mark": ";", "sentence": 2},
        {"rule": "1.1", "kind": "not_approved", "token": "water", "sentences": [0, 1]},
        {"rule": "1.1", "kind": "not_approved", "token": "pump", "sentences": [2]},
    ],
}


def test_parse_report():
    assert parse_report(REPORT) == Checked(
        ok=False,
        findings=3,
        by_kind={"punctuation": 1, "not_approved": 2},
        words=("water", "pump"),
        version="v0.1.1",
        mode="description",
    )


def test_parse_report_without_summary():
    """The vendored checker (170c269) emits no summary block."""
    old = {k: v for k, v in REPORT.items() if k != "summary"}
    assert parse_report(old) == parse_report(REPORT)


def test_locate_fails_fast_without_member(tmp_path):
    with pytest.raises(SystemExit, match="no asd-ste100/scripts"):
        CheckerCli.locate(tmp_path, "description")


def test_empty_text_skips_without_a_process():
    checker = CheckerCli(Path("/nonexistent"))
    assert checker("  \n", ()) == Skipped("empty")


def skills_root():
    for root in (os.environ.get("STE_TAX_SKILLS"), ".github/skills"):
        if (
            root
            and (Path(root) / "asd-ste100" / "scripts" / "pyproject.toml").is_file()
        ):
            return Path(root)
    return None


@pytest.mark.skipif(
    skills_root() is None or shutil.which("uv") is None,
    reason="no SKILLs checkout (set STE_TAX_SKILLS or init the submodule)",
)
def test_live_checker_allows_declared_terms():
    check = CheckerCli.locate(skills_root(), "description")
    got = check("Remove the pumps. Answer: 200", ("pump", "Answer"))
    if isinstance(got, Skipped):  # no network for the first fetch
        pytest.skip(got.reason)
    assert got.ok and got.findings == 0
    flagged = check("Remove the pump.", ())
    assert not flagged.ok and "pump" in flagged.words
