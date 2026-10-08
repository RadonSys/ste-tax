"""Naive rate on fixtures; checker report parsing; one live checker
call when a SKILLs checkout is present."""

import os
import shutil
from pathlib import Path

import pytest

from eval.compliance import (
    CheckerCli,
    Gate,
    default_gate,
    default_trie,
    dictionary_words,
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


# Gate row 4 of docs/checker-validation.md, on fixtures. Known words:
# fuel, pump, failure, bolt (+ form bolts), turn off; H: fuel, bolts.
GATE = Gate(
    known=frozenset({"fuel", "pump", "failure", "bolt", "bolts", "turn off"}),
    h=frozenset({"fuel", "bolts"}),
)


def report(*findings):
    return {
        "version": "v0.1.2",
        "mode": "description",
        "ok": not findings,
        "findings": list(findings),
    }


def na(token, **extra):
    return {"kind": "not_approved", "token": token, **extra}


@pytest.mark.parametrize(
    ("findings", "gate_ok", "kept"),
    [
        ((), True, 0),
        # dropped: unknown word, H token, H form, ing_form
        ((na("zorbax"),), True, 0),
        ((na("Fuel"),), True, 0),
        ((na("bolts", headword="bolt"),), True, 0),
        (({"kind": "ing_form", "token": "holding", "verb": "hold"},), True, 0),
        # kept: dictionary word not in H, a form linked to a headword,
        # a multi-word headword, every form finding
        ((na("pump"),), False, 1),
        ((na("Utilize", headword="utilize"),), False, 1),
        ((na("turn off"),), False, 1),
        (({"kind": "sentence_length", "sentence": 0},), False, 1),
        (({"kind": "punctuation", "mark": ";"},), False, 1),
        ((na("zorbax"), na("failure"), na("fuel")), False, 1),
    ],
)
def test_gate(findings, gate_ok, kept):
    got = parse_report(report(*findings), GATE)
    assert (got.gate_ok, got.gate_findings) == (gate_ok, kept)
    assert got.ok is (not findings)


def test_no_gate_leaves_gate_fields_none():
    got = parse_report(report(na("pump")))
    assert (got.gate_ok, got.gate_findings) == (None, None)


def test_dictionary_words_cover_forms_and_unapproved():
    lex = {
        "approved": [
            {"word": "remove", "forms": ["remove", "removes"], "plural": None},
            {"word": "valve", "forms": ["valve"], "plural": "valves"},
        ],
        "unapproved": [
            {"word": "turn off", "forms": []},
            {"word": "utilize", "forms": ["utilized"]},
        ],
    }
    assert dictionary_words(lex) == {
        "remove",
        "removes",
        "valve",
        "valves",
        "turn off",
        "utilize",
        "utilized",
    }


def test_default_gate_loads_h_and_lexicon():
    g = default_gate()
    assert {"fuel", "pump", "oil"} <= g.h
    assert {"remove", "utilize", "fuel"} <= g.known
    assert "zorbax" not in g.known


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
    assert got.ok and got.findings == 0 and got.gate_ok
    flagged = check("Remove the pump.", ())
    assert not flagged.ok and "pump" in flagged.words
    assert flagged.gate_ok  # pump is an H token
