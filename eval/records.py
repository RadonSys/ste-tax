"""Typed records: task in, generation between, result out.

Every record crosses a JSON boundary through one parser (`parse_task`,
`ArmRecord.from_json`, `WatermarkRecord.from_json`). Inside the
harness, a record is a frozen dataclass and its invariants hold.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Literal, Self


class Kind(StrEnum):
    MATH = "math"
    QA = "qa"
    WRITING = "writing"


class Arm(StrEnum):
    A0 = "A0"  # free-form baseline
    A1 = "A1"  # STE system prompt
    A2 = "A2"  # A0 draft, then STE rewrite


type Answer = int | float | str | None

TASK_KEYS = frozenset(
    {"id", "kind", "prompt", "answer", "technical_terms", "source", "split", "license"}
)
OPTIONAL_TASK_KEYS = frozenset({"meta"})


KIND_VALUES = tuple(k.value for k in Kind)  # tuple: `in` needs no hash


class SchemaError(ValueError):
    """One record broke the schema. Message lists every broken field."""


@dataclass(frozen=True, slots=True)
class Task:
    """One task. Answer type follows kind: math number, qa string,
    writing None (unscored)."""

    id: str
    kind: Kind
    prompt: str
    answer: Answer
    technical_terms: tuple[str, ...]
    source: str
    split: str
    license: str
    meta: dict[str, Any] | None = None


def _nonempty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_number(value: object) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _answer_fits(kind: Kind, answer: object) -> bool:
    match kind:
        case Kind.MATH:
            return _is_number(answer)
        case Kind.QA:
            return _nonempty_str(answer)
        case Kind.WRITING:
            return answer is None


def task_errors(raw: object) -> list[str]:
    """Every schema violation of one decoded JSON value. Empty = valid."""
    if not isinstance(raw, dict):
        return ["record is not a JSON object"]
    errors = []
    missing = TASK_KEYS - raw.keys()
    if missing:
        errors.append(f"missing keys: {', '.join(sorted(missing))}")
    unknown = raw.keys() - TASK_KEYS - OPTIONAL_TASK_KEYS
    if unknown:
        errors.append(f"unknown keys: {', '.join(sorted(unknown))}")
    for key in ("id", "prompt", "source", "split", "license"):
        if key in raw and not _nonempty_str(raw[key]):
            errors.append(f"{key}: need a non-empty string")
    kind = raw.get("kind")
    if "kind" in raw and kind not in KIND_VALUES:
        errors.append(f"kind: {kind!r} is not one of math, qa, writing")
    elif (
        kind in KIND_VALUES
        and "answer" in raw
        and not _answer_fits(Kind(kind), raw["answer"])
    ):
        want = {
            "math": "a finite number",
            "qa": "a non-empty string",
            "writing": "null",
        }
        errors.append(f"answer: kind {kind} needs {want[kind]}")
    terms = raw.get("technical_terms")
    if "technical_terms" in raw and not (
        isinstance(terms, list) and all(map(_nonempty_str, terms))
    ):
        errors.append("technical_terms: need a list of non-empty strings")
    if "meta" in raw and not isinstance(raw["meta"], dict):
        errors.append("meta: need a JSON object")
    return errors


def parse_task(raw: object) -> Task:
    """Smart constructor. Raises SchemaError with every violation."""
    errors = task_errors(raw)
    if errors:
        raise SchemaError("; ".join(errors))
    assert isinstance(raw, dict)
    return Task(
        id=raw["id"],
        kind=Kind(raw["kind"]),
        prompt=raw["prompt"],
        answer=raw["answer"],
        technical_terms=tuple(raw["technical_terms"]),
        source=raw["source"],
        split=raw["split"],
        license=raw["license"],
        meta=raw.get("meta"),
    )


@dataclass(frozen=True, slots=True)
class Generation:
    """One backend call. `think_open`: the rendered prompt already opened
    a think segment, so the output starts inside reasoning.
    `truncated`: generation stopped at the token cap."""

    text: str
    token_ids: tuple[int, ...] | None
    latency_s: float
    think_open: bool = False
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class Checked:
    """The asd-ste100 checker ran. `findings` counts report findings:
    one per distinct unapproved word, one per long sentence, and so on."""

    ok: bool
    findings: int
    by_kind: dict[str, int]
    words: tuple[str, ...]
    version: str
    mode: str
    status: Literal["checked"] = "checked"


@dataclass(frozen=True, slots=True)
class Skipped:
    """The checker did not run. `reason`: off, empty, or error text.
    `rescore` retries every Skipped record except reason empty."""

    reason: str
    status: Literal["skipped"] = "skipped"


type CheckerOutcome = Checked | Skipped


def parse_checker(raw: dict[str, Any]) -> CheckerOutcome:
    match raw:
        case {"status": "checked"}:
            return Checked(
                ok=bool(raw["ok"]),
                findings=int(raw["findings"]),
                by_kind={str(k): int(v) for k, v in raw["by_kind"].items()},
                words=tuple(raw["words"]),
                version=str(raw["version"]),
                mode=str(raw["mode"]),
            )
        case {"status": "skipped", "reason": str(reason)}:
            return Skipped(reason)
        case _:
            raise SchemaError(f"checker outcome: {raw!r}")


@dataclass(frozen=True, slots=True)
class Rewrite:
    """A2 only: the frozen draft and the cost split."""

    draft_text: str
    draft_correct: bool | None
    draft_generated_tokens: int
    draft_reasoning_tokens: int
    rewrite_generated_tokens: int
    rewrite_reasoning_tokens: int


@dataclass(frozen=True, slots=True)
class ArmRecord:
    """One sample of one task under one arm. `sample` is the index in
    0..k-1 (seed + sample). Invariants: `rewrite` is set iff arm A2;
    `correct` None iff kind writing; `fallback_correct` set only when no
    answer line exists, so then `correct` is False; `sample` >= 0."""

    task_id: str
    kind: Kind
    arm: Arm
    sample: int
    model: str
    backend: str
    correct: bool | None
    fallback_correct: bool | None
    degenerate: bool
    truncated: bool
    reasoning_tokens: int
    generated_tokens: int
    output_tokens: int
    latency_s: float
    compliance: float | None
    nonconforming: tuple[str, ...]
    checker: CheckerOutcome
    text: str
    rewrite: Rewrite | None

    def __post_init__(self) -> None:
        where = f"{self.task_id} {self.arm} #{self.sample}"
        if self.sample < 0:
            raise SchemaError(f"{where}: sample must be >= 0")
        if (self.arm is Arm.A2) != (self.rewrite is not None):
            raise SchemaError(f"{where}: rewrite iff A2")
        if (self.kind is Kind.WRITING) != (self.correct is None):
            raise SchemaError(f"{where}: correct is None iff writing")
        if self.fallback_correct is not None and self.correct is not False:
            raise SchemaError(f"{where}: fallback only when correct is False")

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Self:
        fields = dict(raw)
        fields["kind"] = Kind(raw["kind"])
        fields["arm"] = Arm(raw["arm"])
        # Records written before k samples have no index: one sample, 0.
        fields["sample"] = int(raw.get("sample", 0))
        fields["nonconforming"] = tuple(raw["nonconforming"])
        fields["checker"] = parse_checker(raw["checker"])
        rewrite = raw.get("rewrite")
        fields["rewrite"] = None if rewrite is None else Rewrite(**rewrite)
        return cls(**fields)


@dataclass(frozen=True, slots=True)
class WatermarkRecord:
    """Watermark mode: one writing task under A0 or A1."""

    task_id: str
    arm: Arm
    tokens: int
    greens: int
    z_full: float
    matched_len: int
    z_matched: float

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Self:
        return cls(**{**raw, "arm": Arm(raw["arm"])})
