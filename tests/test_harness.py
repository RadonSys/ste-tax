"""Laws of the pure core: answer check, degeneracy, reasoning split,
arms, summary."""

import math

import pytest

from eval.harness import (
    ANSWER_LABEL,
    Context,
    Score,
    allowed_terms,
    check_answer,
    contains_run,
    is_degenerate,
    mean,
    measure,
    run_arm,
    split_think,
    summarize,
)
from eval.records import Arm, ArmRecord, Checked, Generation, Kind, Skipped

from .conftest import task

# ------------------------------------------------------------ answer check


@pytest.mark.parametrize(
    ("gold", "text", "correct"),
    [
        (200, "Answer: 200", True),
        (200, "work...\nAnswer: 200 liters", True),
        (200, "**Answer:** 200", True),
        (1200, "Answer: 1,200", True),
        (200, "Answer: 1,200", False),
        (25.5, "Answer: 25.50", True),
        (-3, "Answer: -3", True),
        (204, "Answer: $204.", True),
        # first number on the answer line, not the last
        (200, "Answer: 200 liters after 8 minutes", True),
        (200, "Answer: 199", False),
        # an answer line with no number is wrong, no fallback
        (200, "So 200. Answer: two hundred", False),
        # the last answer line wins
        (200, "Answer: 100\nAnswer: 200", True),
    ],
)
def test_math_answer_line(gold, text, correct):
    assert check_answer(task("math", gold), text) == Score(correct, None)


@pytest.mark.parametrize(
    ("gold", "text", "fallback"),
    [
        # no answer line: never correct; the last number is the fallback
        (200, "35 * 8 = 280, so 480 - 280 = 200", True),
        (200, "200 at first, then 150", False),
        (200, "", False),
    ],
)
def test_math_fallback(gold, text, fallback):
    assert check_answer(task("math", gold), text) == Score(False, fallback)


@pytest.mark.parametrize(
    ("gold", "text", "correct"),
    [
        ("Au", "Answer: Au", True),
        ("Au", "Answer: Au (gold)", True),
        ("Au", "The gold is Au. Answer: Ag", False),
        ("Saturn", "Answer: Saturnine", False),
        ("central processing unit", "Answer: Central Processing Unit (CPU)", True),
        ("central processing unit", "Answer: CPU", False),
        # an answer line exists: the rest of the text does not count
        ("Canberra", "Not Canberra. Answer: Sydney", False),
    ],
)
def test_qa_answer_line(gold, text, correct):
    assert check_answer(task("qa", gold), text) == Score(correct, None)


@pytest.mark.parametrize(
    ("gold", "text", "fallback"),
    [
        ("Canberra", "The capital is Canberra.", True),
        # whole words: no substring hit inside "because"
        ("Au", "It is because of gold", False),
        # a common-word gold hits almost any text: only a fallback
        ("the", "The answer is unclear.", True),
    ],
)
def test_qa_fallback_is_never_correct(gold, text, fallback):
    assert check_answer(task("qa", gold), text) == Score(False, fallback)


def test_writing_is_unscored():
    assert check_answer(task("writing", None), "Answer: x") == Score(None, None)


def test_contains_run_empty_needle_is_false():
    assert not contains_run(["a"], [])
    assert contains_run(["a", "b", "c"], ["b", "c"])


# ------------------------------------------------------------- degeneracy


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("", True),
        ("   ", True),
        ("ok", True),
        ("I'm sorry, I cannot help.", True),
        ("  I can’t do that task.", True),
        ("Remove the cover.", False),
        ("5 6", False),
    ],
)
def test_degenerate(text, want):
    assert is_degenerate(text) is want


# --------------------------------------------------------- reasoning split


START, END = 100, 101


@pytest.mark.parametrize(
    ("ids", "think_open", "reasoning", "final"),
    [
        ((START, 1, 2, END, 3), False, (1, 2), (3,)),
        ((0, START, 1, END, 3), False, (1,), (0, 3)),
        # template opened the segment: only the end tag is generated
        ((1, 2, END, 3), True, (1, 2), (3,)),
        ((1, 2, END, 3), False, (1, 2), (3,)),
        # unclosed: the rest is reasoning
        ((START, 1, 2), False, (1, 2), ()),
        # cut at the cap inside a template-opened segment
        ((1, 2), True, (1, 2), ()),
        ((1, 2), False, (), (1, 2)),
        ((), False, (), ()),
    ],
)
def test_split_think_ids(ids, think_open, reasoning, final):
    r, f = split_think(ids, START, END, think_open)
    assert (tuple(r), tuple(f)) == (reasoning, final)


@pytest.mark.parametrize("think_open", [False, True])
@pytest.mark.parametrize(
    "ids", [(START, 1, END, 2), (1, END, 2), (START, 1), (1, 2), ()]
)
def test_split_think_partitions(ids, think_open):
    """Law: reasoning + final + tags = the whole sequence (as a multiset)."""
    r, f = split_think(ids, START, END, think_open)
    tags = [i for i in ids if i in (START, END)]
    assert sorted([*r, *f, *tags]) == sorted(ids)


@pytest.mark.parametrize(
    ("text", "think_open", "reasoning", "final"),
    [
        ("<think>a b</think>c d", False, 2, "c d"),
        ("c d", False, 0, "c d"),
        ("a b</think>c d", True, 2, "c d"),
        ("<think>a b", False, 2, ""),
        ("a b", True, 2, ""),
    ],
)
def test_measure_text(text, think_open, reasoning, final):
    m = measure(Generation(text, None, 0.0, think_open=think_open), None)
    assert (m.reasoning_tokens, m.final_text) == (reasoning, final)
    assert m.generated_tokens == len(text.split())


class FakeTok:
    """Tokenizer over ids; decode joins ids as words."""

    def think_ids(self):
        return START, END

    def decode(self, ids):
        return " ".join(map(str, ids))

    def count(self, text):
        return len(text.split())


def test_measure_ids_uses_tokenizer():
    gen = Generation("ignored", (START, 1, 2, END, 7, 8), 0.0)
    m = measure(gen, FakeTok())
    assert (m.reasoning_tokens, m.generated_tokens, m.final_text) == (2, 6, "7 8")


# ------------------------------------------------------------------- arms


def scripted(*outputs):
    """generate() that returns the outputs in order and logs messages."""
    calls = []
    it = iter(outputs)

    def generate(messages):
        calls.append(messages)
        return Generation(next(it), None, 1.5)

    return generate, calls


def ctx(wordlist="REMOVE (V)"):
    return Context("m", "mock", wordlist, None, lambda text, terms: (1.0, ()))


def test_a0_plain_prompt():
    gen, calls = scripted("<think>x</think>Answer: 200")
    r = run_arm(gen, task(), Arm.A0, ctx())
    assert [m["role"] for m in calls[0]] == ["user"]
    assert (r.correct, r.fallback_correct, r.reasoning_tokens) == (True, None, 1)
    assert r.rewrite is None
    assert r.checker == Skipped("pending")


def test_a1_system_prompt_carries_wordlist_and_terms():
    gen, calls = scripted("Answer: 200")
    run_arm(gen, task(terms=["OHM"]), Arm.A1, ctx())
    system = calls[0][0]["content"]
    assert "REMOVE (V)" in system and "OHM" in system


def test_a1_without_wordlist():
    gen, calls = scripted("Answer: 200")
    run_arm(gen, task(), Arm.A1, ctx(wordlist=None))
    assert "Approved words:" not in calls[0][0]["content"]


def test_a2_rewrites_frozen_draft_and_sums_cost():
    gen, calls = scripted(
        "<think>a b</think>Draft. Answer: 199", "<think>c</think>Fixed. Answer: 200"
    )
    r = run_arm(gen, task(), Arm.A2, ctx())
    assert "Draft. Answer: 199" in calls[1][-1]["content"]
    assert r.rewrite.draft_correct is False and r.correct is True
    assert r.reasoning_tokens == 3
    assert (
        r.generated_tokens
        == r.rewrite.draft_generated_tokens + r.rewrite.rewrite_generated_tokens
    )
    assert r.latency_s == 3.0


def test_answer_label_allowed_for_scored_kinds_only():
    assert ANSWER_LABEL in allowed_terms(task("qa", "x"))
    assert allowed_terms(task("writing", None, ["BATTERY"])) == ("BATTERY",)


# ---------------------------------------------------------------- summary


def record(
    arm,
    correct,
    compliance,
    checker,
    gen=10,
    fallback=None,
    truncated=False,
    sample=0,
):
    return ArmRecord(
        "t",
        Kind.WRITING if correct is None else Kind.MATH,
        arm,
        sample,
        "m",
        "mock",
        correct,
        fallback,
        False,
        truncated,
        1,
        gen,
        5,
        1.0,
        compliance,
        (),
        checker,
        "x",
        None,
    )


def test_mean_empty_is_nan():
    assert math.isnan(mean([])) and mean([1, 2]) == 1.5


def test_summary_skips_none_and_unchecked():
    ok = Checked(True, 0, {}, (), "v0.1.1", "description")
    bad = Checked(False, 2, {"not_approved": 2}, ("a", "b"), "v0.1.1", "description")
    rs = [
        record(Arm.A0, True, 1.0, ok),
        record(Arm.A0, None, None, Skipped("off")),
        record(Arm.A0, False, 0.5, bad),
    ]
    line = summarize(rs).splitlines()[0]
    assert "acc=0.500" in line and "compliance=0.750" in line
    assert "checker_ok=0.500" in line and "(checked 2/3)" in line


def test_truncated_answer_leaves_accuracy():
    off = Skipped("off")
    rs = [
        record(Arm.A0, True, 1.0, off),
        record(Arm.A0, False, 1.0, off, truncated=True),
    ]
    line = summarize(rs).splitlines()[0]
    assert "acc=1.000" in line and "truncated=1" in line


def test_fallback_hits_counted_not_correct():
    off = Skipped("off")
    rs = [
        record(Arm.A0, False, 1.0, off, fallback=True),
        record(Arm.A0, True, 1.0, off),
    ]
    line = summarize(rs).splitlines()[0]
    assert "acc=0.500" in line and "no_answer_line=1 (fallback hits 1)" in line


def test_summary_mean_and_spread_over_samples():
    """Accuracy per sample: 1.0, 0.0, 0.5 -> mean 0.5, sd 0.5. Counts sum."""
    off = Skipped("off")
    rs = [
        record(Arm.A0, True, 1.0, off, sample=0),
        record(Arm.A0, False, 1.0, off, sample=1),
        record(Arm.A0, True, 1.0, off, sample=2, truncated=True),
        record(Arm.A0, False, 1.0, off, sample=2),
        record(Arm.A0, True, 1.0, off, sample=2),
    ]
    line = summarize(rs).splitlines()[0]
    assert line.startswith("A0: k=3 n=5 acc=0.500±0.500")
    assert "truncated=1" in line and "gen_tok=10.0±0.0" in line


def test_one_sample_spread_is_zero():
    line = summarize([record(Arm.A0, True, 1.0, Skipped("off"))]).splitlines()[0]
    assert "k=1" in line and "acc=1.000±0.000" in line


def test_run_arm_keeps_sample_index():
    gen, _ = scripted("Answer: 200")
    assert run_arm(gen, task(), Arm.A0, ctx(), sample=2).sample == 2


def test_summary_tax_against_a0():
    off = Skipped("off")
    rs = [
        record(Arm.A0, True, 0.5, off, gen=10),
        record(Arm.A1, False, 0.9, off, gen=25),
    ]
    tax = summarize(rs).splitlines()[-1]
    assert tax.startswith("tax A1-A0: acc -1.000, gen_tok x2.50")
    assert "compliance +0.400" in tax
