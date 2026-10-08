"""Task schema rejections, record round trips, loader."""

import json
from dataclasses import replace

import pytest

from eval import loader
from eval.records import (
    Arm,
    ArmRecord,
    Checked,
    Kind,
    Rewrite,
    SchemaError,
    Skipped,
    WatermarkRecord,
    parse_task,
)

GOOD = {
    "id": "gsm8k-test-0001",
    "kind": "math",
    "prompt": "2 + 2? End with 'Answer: <number>'.",
    "answer": 4,
    "technical_terms": [],
    "source": "gsm8k",
    "split": "test",
    "license": "MIT",
}


def test_good_task_parses():
    t = parse_task(GOOD)
    assert t.kind is Kind.MATH and t.technical_terms == () and t.meta is None


def test_meta_is_optional_object():
    assert parse_task({**GOOD, "meta": {"index": 1}}).meta == {"index": 1}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": ""}, "id: need a non-empty string"),
        ({"kind": "code"}, "kind: 'code' is not one of"),
        ({"kind": ["math"]}, "kind: ['math'] is not one of"),
        ({"answer": "4"}, "answer: kind math needs a finite number"),
        ({"answer": True}, "answer: kind math needs a finite number"),
        ({"answer": float("nan")}, "answer: kind math needs a finite number"),
        ({"kind": "qa", "answer": 4}, "answer: kind qa needs a non-empty string"),
        ({"kind": "writing", "answer": "x"}, "answer: kind writing needs null"),
        ({"technical_terms": "OHM"}, "technical_terms: need a list"),
        ({"technical_terms": ["OHM", ""]}, "technical_terms: need a list"),
        ({"source": None}, "source: need a non-empty string"),
        ({"extra": 1}, "unknown keys: extra"),
        ({"meta": []}, "meta: need a JSON object"),
    ],
)
def test_schema_rejections(change, message):
    with pytest.raises(
        SchemaError, match=message.replace("[", r"\[").replace("]", r"\]")
    ):
        parse_task({**GOOD, **change})


def test_missing_keys_listed():
    raw = {k: v for k, v in GOOD.items() if k not in ("split", "license")}
    with pytest.raises(SchemaError, match="missing keys: license, split"):
        parse_task(raw)


def test_non_object_rejected():
    with pytest.raises(SchemaError, match="not a JSON object"):
        parse_task([GOOD])


# ------------------------------------------------------------------ loader


def lines(*records):
    return [json.dumps(r) for r in records]


def test_loader_collects_every_error():
    bad = {**GOOD, "id": "b", "kind": "code"}
    with pytest.raises(loader.TaskError) as e:
        loader.parse_lines([("a.jsonl", ["{", *lines(bad)]), ("b.jsonl", lines(GOOD))])
    assert len(e.value.errors) == 2
    assert e.value.errors[0].startswith("a.jsonl:1: bad JSON")
    assert e.value.errors[1].startswith("a.jsonl:2: kind")


def test_loader_rejects_duplicate_id_across_files():
    with pytest.raises(
        loader.TaskError, match=r"b.jsonl:1: duplicate id .* \(first at a.jsonl:2\)"
    ):
        loader.parse_lines([("a.jsonl", ["", *lines(GOOD)]), ("b.jsonl", lines(GOOD))])


def test_loader_skips_blank_lines_keeps_order():
    second = {**GOOD, "id": "z"}
    got = loader.parse_lines([("a", ["", *lines(second), "  ", *lines(GOOD)])])
    assert [t.id for t in got] == ["z", GOOD["id"]]


def test_expand_rejects_empty_glob(tmp_path):
    with pytest.raises(loader.TaskError, match="no file matches"):
        loader.expand([str(tmp_path / "*.jsonl")])


def test_expand_dedups(tmp_path):
    (tmp_path / "a.jsonl").write_text("")
    pattern = str(tmp_path / "*.jsonl")
    assert len(loader.expand([pattern, pattern])) == 1


def test_sample_is_seeded_ordered_subset():
    tasks = [parse_task({**GOOD, "id": str(i)}) for i in range(20)]
    a, b = loader.sample(tasks, 5, 0), loader.sample(tasks, 5, 0)
    assert a == b and len(a) == 5
    idx = [tasks.index(t) for t in a]
    assert idx == sorted(idx)
    assert loader.sample(tasks, 5, 1) != a
    assert loader.sample(tasks, None, 0) == tasks == loader.sample(tasks, 99, 0)


def test_shipped_task_files_validate():
    assert loader.load(loader.default_paths())


# --------------------------------------------------------------- records


CHECKED = Checked(
    False, 2, {"not_approved": 2}, ("pump", "water"), "v0.1.1", "description"
)
REWRITE = Rewrite("draft", True, 10, 4, 8, 2)


def arm_record(arm=Arm.A0, checker=CHECKED, rewrite=None, sample=0):
    return ArmRecord(
        "t",
        Kind.MATH,
        arm,
        sample,
        "m",
        "mock",
        True,
        None,
        False,
        False,
        4,
        10,
        6,
        0.5,
        0.75,
        ("PUMP",),
        checker,
        "text",
        rewrite,
    )


@pytest.mark.parametrize(
    "rec",
    [
        arm_record(),
        arm_record(checker=Skipped("off")),
        arm_record(Arm.A2, rewrite=REWRITE),
        arm_record(sample=2),
        replace(arm_record(), compliance=None, correct=False, fallback_correct=True),
        replace(arm_record(), kind=Kind.WRITING, correct=None),
    ],
)
def test_arm_record_round_trip(rec):
    """Law: from_json . json . to_json = id."""
    assert ArmRecord.from_json(json.loads(json.dumps(rec.to_json()))) == rec


@pytest.mark.parametrize(("arm", "rewrite"), [(Arm.A2, None), (Arm.A1, REWRITE)])
def test_rewrite_iff_a2(arm, rewrite):
    with pytest.raises(SchemaError, match="rewrite iff A2"):
        arm_record(arm, rewrite=rewrite)


@pytest.mark.parametrize(
    "change",
    [
        {"correct": None},  # math must be scored
        {"kind": Kind.WRITING},  # writing must not be
        {"correct": True, "fallback_correct": True},
    ],
)
def test_score_invariants(change):
    with pytest.raises(SchemaError):
        replace(arm_record(), **change)


def test_record_without_sample_reads_as_sample_0():
    """Records written before k samples carry no index."""
    raw = arm_record(sample=0).to_json()
    del raw["sample"]
    assert ArmRecord.from_json(raw) == arm_record(sample=0)


def test_negative_sample_rejected():
    with pytest.raises(SchemaError, match="sample"):
        arm_record(sample=-1)


def test_unknown_checker_status_rejected():
    raw = arm_record().to_json() | {"checker": {"status": "maybe"}}
    with pytest.raises(SchemaError, match="checker outcome"):
        ArmRecord.from_json(raw)


def test_watermark_record_round_trip():
    r = WatermarkRecord("w", Arm.A1, 200, 80, 3.2, 150, 2.9)
    assert WatermarkRecord.from_json(json.loads(json.dumps(r.to_json()))) == r
