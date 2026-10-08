"""STE-tax eval: pure core. Arms, answer check, degeneracy, reasoning
split, metrics, summary. No I/O here; the shell is eval/cli.py.

Design: docs/design.md and docs/intervention-pin.md.

Arms (default run order A0, A2, A1, per the pin):
- A0: free-form baseline. No STE instruction.
- A1: STE system prompt with the approved word list (`--wordlist`).
- A2: A0 draft first (reasoning frozen), then a rewrite pass that may
  change surface form only. Cost is draft + rewrite. The record keeps
  the draft's own correctness, so a rewrite that fixes or breaks the
  answer shows.

Per task, arm, and sample (k samples, seed + sample index): correct (final text, after the think segment),
reasoning_tokens, generated_tokens, output_tokens, latency_s,
compliance (naive rate), checker outcome, degenerate, truncated.
"""

from __future__ import annotations

import math
import re
import statistics
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from scripts import validate as ste_validate

from .records import (
    Arm,
    ArmRecord,
    Checked,
    Generation,
    Kind,
    Rewrite,
    Skipped,
    Task,
)

REFUSAL_OPENERS = (
    "I cannot",
    "I can't",
    "I'm sorry",
    "I am sorry",
    "I’m sorry",
    "I can’t",
)

STE_SYSTEM = """You write in ASD-STE100 Simplified Technical English.
Rules:
- Use only words from the approved word list below.
- One meaning per word. Keep sentences short.
- You may also use numbers, and these technical terms: {technical}
Approved words:
{approved}"""

STE_SYSTEM_NO_LIST = """You write in ASD-STE100 Simplified Technical English.
Rules:
- Use only words that the ASD-STE100 dictionary approves.
- One meaning per word. Keep sentences short.
- You may also use numbers, and these technical terms: {technical}"""

REWRITE_USER = """Rewrite the text below in ASD-STE100 Simplified Technical English. Change the surface form only. Do not change facts, numbers, or the final answer line.

{text}"""

THINK_START = "<think>"
THINK_END = "</think>"

type Message = dict[str, str]
type Messages = list[Message]
type Generate = Callable[[Messages], Generation]
type CheckText = Callable[[str, tuple[str, ...]], object]


class Tokenizer(Protocol):
    """What the core needs from a backend tokenizer."""

    def think_ids(self) -> tuple[int, int]: ...
    def decode(self, ids: Sequence[int]) -> str: ...
    def count(self, text: str) -> int: ...


# --------------------------------------------------------------- prompts


def approved_id_list(lexicon: dict) -> str:
    """Compact 'WORD (POS)' list for the A1/A2 system prompt."""
    return ", ".join(sorted(e["id"].upper() for e in lexicon["approved"]))


def ste_system(task: Task, wordlist: str | None) -> str:
    """wordlist None: the STE instruction without the list."""
    technical = ", ".join(task.technical_terms) or "none"
    if wordlist is None:
        return STE_SYSTEM_NO_LIST.format(technical=technical)
    return STE_SYSTEM.format(technical=technical, approved=wordlist)


def plain(content: str) -> Messages:
    return [{"role": "user", "content": content}]


def ste(task: Task, wordlist: str | None, content: str) -> Messages:
    return [
        {"role": "system", "content": ste_system(task, wordlist)},
        {"role": "user", "content": content},
    ]


# ---------------------------------------------------------- answer check


ANSWER_LINE = re.compile(r"Answer:\s*(.+)")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
NON_ALNUM = re.compile(r"[^a-z0-9 ]")


def final_answer_line(text: str) -> str | None:
    """The last 'Answer: ...' line, or None."""
    found = ANSWER_LINE.findall(text)
    return found[-1].strip() if found else None


def words(s: str) -> list[str]:
    return NON_ALNUM.sub(" ", s.lower()).split()


def contains_run(hay: list[str], needle: list[str]) -> bool:
    """needle is a whole-word run of hay. Words hold no spaces, so a
    padded substring test is exact."""
    return bool(needle) and f" {' '.join(needle)} " in f" {' '.join(hay)} "


@dataclass(frozen=True, slots=True)
class Score:
    """`correct`: judged on the last answer line only; no line is wrong.
    `fallback`: set only when no answer line exists; the gold found
    anywhere in the text. A weaker outcome, never counted as correct.
    Both None for writing."""

    correct: bool | None
    fallback: bool | None


def number_is(gold: float, nums: list[str]) -> bool:
    return bool(nums) and math.isclose(float(nums[0]), gold, rel_tol=0, abs_tol=1e-6)


def check_answer(task: Task, final_text: str) -> Score:
    """math: the first number on the answer line; fallback: the last
    number in the text. qa: the gold words as a whole-word run in the
    answer line; fallback: in the text."""
    gold = task.answer
    line = final_answer_line(final_text)
    match task.kind:
        case Kind.WRITING:
            return Score(None, None)
        case Kind.MATH:
            assert isinstance(gold, int | float)
            if line is not None:
                return Score(
                    number_is(gold, NUMBER.findall(line.replace(",", ""))), None
                )
            nums = NUMBER.findall(final_text.replace(",", ""))[-1:]
            return Score(False, number_is(gold, nums))
        case Kind.QA:
            needle = words(str(gold))
            if line is not None:
                return Score(contains_run(words(line), needle), None)
            return Score(False, contains_run(words(final_text), needle))


# The answer-line label the prompts demand. Not an STE word; allowed in
# compliance for scored tasks, so the format itself is no violation.
ANSWER_LABEL = "Answer"


def allowed_terms(task: Task) -> tuple[str, ...]:
    """Technical terms for compliance: the task's, plus the answer label
    for scored kinds."""
    if task.kind is Kind.WRITING:
        return task.technical_terms
    return (*task.technical_terms, ANSWER_LABEL)


def is_degenerate(final_text: str) -> bool:
    """Empty or near-empty output, or a refusal opening."""
    if len(ste_validate.tokenize(final_text)) < 2:
        return True
    return final_text.lstrip().startswith(REFUSAL_OPENERS)


# ------------------------------------------------------- reasoning split


def split_think[T](
    seq: Sequence[T], start: T, end: T, think_open: bool
) -> tuple[Sequence[T], Sequence[T]]:
    """(reasoning, final) of one generation, over ids or text segments.

    - end present: reasoning runs from after a preceding start (or from
      the beginning when none) to the first end.
    - start only: unclosed segment; the rest is reasoning.
    - neither, prompt opened the segment: all reasoning (cut at cap).
    - neither, prompt did not: no reasoning.
    """
    if end in seq:
        j = list(seq).index(end)
        head = seq[:j]
        if start in head:
            i = list(head).index(start)
            return seq[i + 1 : j], [*seq[:i], *seq[j + 1 :]]
        return head, seq[j + 1 :]
    if start in seq:
        i = list(seq).index(start)
        return seq[i + 1 :], seq[:i]
    if think_open:
        return seq, seq[:0]
    return seq[:0], seq


THINK_TAG = re.compile(f"({re.escape(THINK_START)}|{re.escape(THINK_END)})")


@dataclass(frozen=True, slots=True)
class Measured:
    reasoning_tokens: int
    generated_tokens: int
    final_text: str


def measure(gen: Generation, tok: Tokenizer | None) -> Measured:
    """Token counts from ids when the backend has a tokenizer, else
    whitespace words over the text."""
    if tok is not None and gen.token_ids is not None:
        start, end = tok.think_ids()
        reasoning, final = split_think(gen.token_ids, start, end, gen.think_open)
        return Measured(len(reasoning), len(gen.token_ids), tok.decode(final))
    parts = THINK_TAG.split(gen.text)
    r_parts, f_parts = split_think(parts, THINK_START, THINK_END, gen.think_open)
    return Measured(
        len("".join(r_parts).split()),
        len(gen.text.split()),
        "".join(f_parts).strip(),
    )


def count_tokens(text: str, tok: Tokenizer | None) -> int:
    return tok.count(text) if tok is not None else len(text.split())


# ------------------------------------------------------------------- arms


@dataclass(frozen=True, slots=True)
class Context:
    """Run-constant inputs of every arm."""

    model: str
    backend: str
    wordlist: str | None
    tokenizer: Tokenizer | None
    naive: Callable[[str, tuple[str, ...]], tuple[float | None, tuple[str, ...]]]


def run_arm(
    generate: Generate, task: Task, arm: Arm, ctx: Context, sample: int = 0
) -> ArmRecord:
    """One record for (task, arm, sample). Effects only through
    `generate`, which the shell seeds per sample; A2 sequences two
    calls, the rewrite reads the draft. The checker runs later over the
    whole run, so `checker` starts as Skipped("pending")."""
    tok = ctx.tokenizer
    rewrite = None
    match arm:
        case Arm.A0 | Arm.A1:
            messages = (
                plain(task.prompt)
                if arm is Arm.A0
                else ste(task, ctx.wordlist, task.prompt)
            )
            gen = generate(messages)
            m = measure(gen, tok)
            reasoning, generated = m.reasoning_tokens, m.generated_tokens
            latency, truncated = gen.latency_s, gen.truncated
        case Arm.A2:
            # ponytail: A2 regenerates the A0 draft. With one seed per
            # sample (vLLM per-request seed) it equals the A0 arm's
            # sample; reuse that output if GPU time binds.
            draft = generate(plain(task.prompt))
            d = measure(draft, tok)
            gen = generate(
                ste(task, ctx.wordlist, REWRITE_USER.format(text=d.final_text))
            )
            m = measure(gen, tok)
            rewrite = Rewrite(
                draft_text=d.final_text,
                draft_correct=check_answer(task, d.final_text).correct,
                draft_generated_tokens=d.generated_tokens,
                draft_reasoning_tokens=d.reasoning_tokens,
                rewrite_generated_tokens=m.generated_tokens,
                rewrite_reasoning_tokens=m.reasoning_tokens,
            )
            reasoning = d.reasoning_tokens + m.reasoning_tokens
            generated = d.generated_tokens + m.generated_tokens
            latency = draft.latency_s + gen.latency_s
            truncated = draft.truncated or gen.truncated
    final = m.final_text
    rate, nonconforming = ctx.naive(final, allowed_terms(task))
    score = check_answer(task, final)
    return ArmRecord(
        task_id=task.id,
        kind=task.kind,
        arm=arm,
        sample=sample,
        model=ctx.model,
        backend=ctx.backend,
        correct=score.correct,
        fallback_correct=score.fallback,
        degenerate=is_degenerate(final),
        truncated=truncated,
        reasoning_tokens=reasoning,
        generated_tokens=generated,
        output_tokens=count_tokens(final, tok),
        latency_s=round(latency, 3),
        compliance=None if rate is None else round(rate, 4),
        nonconforming=nonconforming[:50],
        checker=Skipped("pending"),
        text=final,
        rewrite=rewrite,
    )


# ---------------------------------------------------------------- summary


def mean(xs: Iterable[float]) -> float:
    """Arithmetic mean; NaN on empty, so an absent metric prints nan."""
    values = list(xs)
    return statistics.fmean(values) if values else math.nan


@dataclass(frozen=True, slots=True)
class ArmStats:
    """Means of one arm over one set of records (one sample index)."""

    n: int
    accuracy: float
    no_line: int
    fallback_hits: int
    generated: float
    reasoning: float
    latency: float
    compliance: float
    degenerate: int
    truncated: int
    checked: int
    checker_ok: float
    findings: float


def arm_stats(rs: Sequence[ArmRecord]) -> ArmStats:
    checked = [r.checker for r in rs if isinstance(r.checker, Checked)]
    return ArmStats(
        n=len(rs),
        # truncated answers leave the denominator: cut short is not wrong
        accuracy=mean(
            float(r.correct) for r in rs if r.correct is not None and not r.truncated
        ),
        no_line=sum(r.fallback_correct is not None for r in rs),
        fallback_hits=sum(r.fallback_correct is True for r in rs),
        generated=mean(r.generated_tokens for r in rs),
        reasoning=mean(r.reasoning_tokens for r in rs),
        latency=mean(r.latency_s for r in rs),
        compliance=mean(r.compliance for r in rs if r.compliance is not None),
        degenerate=sum(r.degenerate for r in rs),
        truncated=sum(r.truncated for r in rs),
        checked=len(checked),
        checker_ok=mean(float(c.ok) for c in checked),
        findings=mean(c.findings for c in checked),
    )


# Mean metrics: averaged over samples (avg@k), with the sd across the k
# per-sample means as the spread. Count fields are summed.
MEANS = (
    "accuracy",
    "generated",
    "reasoning",
    "latency",
    "compliance",
    "checker_ok",
    "findings",
)
COUNTS = ("n", "no_line", "fallback_hits", "degenerate", "truncated", "checked")


@dataclass(frozen=True, slots=True)
class Spread:
    mean: float
    sd: float  # sd across the k per-sample means; 0.0 when k = 1

    def show(self, fmt: str) -> str:
        return f"{self.mean:{fmt}}±{self.sd:{fmt}}"


@dataclass(frozen=True, slots=True)
class ArmSummary:
    k: int
    counts: dict[str, int]
    means: dict[str, Spread]


def finite(xs: Iterable[float]) -> list[float]:
    return [x for x in xs if not math.isnan(x)]


def arm_summary(rs: Sequence[ArmRecord]) -> ArmSummary:
    """One arm over all samples: per-sample ArmStats, then the mean and
    sd of each mean metric over samples. A sample whose metric is NaN
    (nothing to average) leaves that metric's mean and sd."""
    per = [
        arm_stats([r for r in rs if r.sample == i])
        for i in sorted({r.sample for r in rs})
    ]
    means = {}
    for f in MEANS:
        xs = finite(getattr(s, f) for s in per)
        sd = statistics.stdev(xs) if len(xs) > 1 else (0.0 if xs else math.nan)
        means[f] = Spread(mean(xs), sd)
    counts = {f: sum(getattr(s, f) for s in per) for f in COUNTS}
    return ArmSummary(len(per), counts, means)


def ratio(a: float, b: float) -> float:
    return a / b if b else math.nan


def summarize(records: Sequence[ArmRecord]) -> str:
    """Per arm: mean±sd over the k samples of each mean metric, summed
    counts. Then the tax of each arm against A0, on the means."""
    stats = {
        arm: arm_summary([r for r in records if r.arm is arm])
        for arm in sorted({r.arm for r in records})
    }

    def line(arm: Arm, s: ArmSummary) -> str:
        m, c = s.means, s.counts
        return (
            f"{arm}: k={s.k} n={c['n']} acc={m['accuracy'].show('.3f')} "
            f"no_answer_line={c['no_line']} "
            f"(fallback hits {c['fallback_hits']}) "
            f"gen_tok={m['generated'].show('.1f')} "
            f"reason_tok={m['reasoning'].show('.1f')} "
            f"latency={m['latency'].show('.2f')}s "
            f"compliance={m['compliance'].show('.3f')} "
            f"checker_ok={m['checker_ok'].show('.3f')} "
            f"findings={m['findings'].show('.2f')} "
            f"(checked {c['checked']}/{c['n']}) "
            f"degenerate={c['degenerate']} truncated={c['truncated']}"
        )

    lines = [line(arm, s) for arm, s in stats.items()]
    if Arm.A0 in stats:
        b = {f: v.mean for f, v in stats[Arm.A0].means.items()}
        for arm, s in stats.items():
            if arm is Arm.A0:
                continue
            x = {f: v.mean for f, v in s.means.items()}
            lines.append(
                f"tax {arm}-A0: acc {x['accuracy'] - b['accuracy']:+.3f}, "
                f"gen_tok x{ratio(x['generated'], b['generated']):.2f}, "
                f"reason_tok {x['reasoning'] - b['reasoning']:+.1f}, "
                f"latency x{ratio(x['latency'], b['latency']):.2f}, "
                f"compliance {x['compliance'] - b['compliance']:+.3f}, "
                f"checker_ok {x['checker_ok'] - b['checker_ok']:+.3f}"
            )
    return "\n".join(lines)
