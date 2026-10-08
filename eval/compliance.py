"""Compliance two ways: the naive vocabulary rate and the skill's checker.

Naive: in-process trie over data/lexicon.json (scripts/validate.py).
Kept for continuity with the first runs.

Checker: `btm-asd-ste100 check` from the asd-ste100 skill, one process
per text, through the skill's documented binding. The checker reads
the pinned ste-tax release (default v0.1.1, equal to data/ at 7111feb)
and downloads it on first use, so it needs network once per cache.
`parse_report` is pure; `CheckerCli` is the effect.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from scripts import validate as ste_validate

from .records import Checked, CheckerOutcome, Skipped

type Trie = dict[str, Any]
type Check = Callable[[str, tuple[str, ...]], CheckerOutcome]

CHECKER_MEMBER = Path("asd-ste100") / "scripts"


# ------------------------------------------------------------------ naive


@cache
def default_trie() -> Trie:
    with open(ste_validate.LEXICON, encoding="utf-8") as f:
        return ste_validate.build_trie(ste_validate.approved_phrases(json.load(f)))


def plurals(word: str) -> tuple[str, ...]:
    """Regular plurals of an uppercase noun: +S, +ES, consonant Y to IES."""
    ies = word.endswith("Y") and len(word) > 1 and word[-2] not in "AEIOU"
    return (word + "S", word + "ES", *([word[:-1] + "IES"] if ies else []))


def term_phrases(technical_terms: Iterable[str]) -> list[str]:
    """Each declared term as a token phrase, and with its last word in
    a regular plural. Matches the checker's allow rule: a multi-word
    term counts only whole, and a term passes in its regular plural."""
    out = []
    for term in technical_terms:
        toks = ste_validate.tokenize(term)
        if toks:
            out.append(" ".join(toks))
            out.extend(" ".join([*toks[:-1], p]) for p in plurals(toks[-1]))
    return out


def naive_compliance(
    text: str, technical_terms: Iterable[str], trie: Trie
) -> tuple[float | None, tuple[str, ...]]:
    """Rate in [0, 1], or None when the text has no scorable tokens.

    Numbers leave the denominator; declared technical terms too, by
    longest match over the term phrases. Empty output must not read as
    fully compliant: degeneracy is its own flag and the compliance mean
    skips None.
    """
    toks = [t for t in ste_validate.tokenize(text) if not t.isdigit()]
    terms = ste_validate.build_trie(term_phrases(technical_terms))
    _, rest = ste_validate.validate(" ".join(toks), terms)
    if not rest:
        return None, ()
    conforming, nonconforming = ste_validate.validate(" ".join(rest), trie)
    good = sum(len(p.split()) for p in conforming)
    return good / (good + len(nonconforming)), tuple(sorted(set(nonconforming)))


# ---------------------------------------------------------------- checker


def parse_report(report: Mapping[str, Any]) -> Checked:
    """`check` JSON report to a Checked outcome. Pure.

    Reads only `ok`, `findings` (each with `kind`), `version`, and
    `mode`: the fields both the vendored submodule's checker (170c269)
    and the current one emit. The current `summary` block is newer.
    """
    findings = report["findings"]
    return Checked(
        ok=bool(report["ok"]),
        findings=len(findings),
        by_kind=dict(Counter(str(f["kind"]) for f in findings)),
        words=tuple(f["token"] for f in findings if f["kind"] == "not_approved"),
        version=str(report["version"]),
        mode=str(report["mode"]),
    )


@dataclass(frozen=True, slots=True)
class CheckerCli:
    """The documented binding, as argv:
    env -u VIRTUAL_ENV uv run --project $(realpath <skill>/scripts)
    btm-asd-ste100 check --text:stdin [--allow:file F] --mode M."""

    project: Path
    mode: str = "description"
    timeout_s: float = 120.0

    @classmethod
    def locate(cls, skills: Path, mode: str) -> CheckerCli:
        """Fail fast before any model loads."""
        project = (skills / CHECKER_MEMBER).resolve()
        if not (project / "pyproject.toml").is_file():
            raise SystemExit(
                f"checker: no {CHECKER_MEMBER} under {skills}. "
                "Run `git submodule update --init`, pass --skills, "
                "or pass --checker off and rescore later."
            )
        if shutil.which("uv") is None:
            raise SystemExit("checker: uv not on PATH; pass --checker off")
        return cls(project, mode)

    # ponytail: one process per text, about 0.45 s each. A batch check
    # command in the skill would remove the startup cost.
    def __call__(self, text: str, technical_terms: tuple[str, ...]) -> CheckerOutcome:
        if not text.strip():
            return Skipped("empty")
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        argv = ["uv", "run", "--project", str(self.project), "btm-asd-ste100"]
        argv += ["check", "--text:stdin", "--mode", self.mode]
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as allow:
            if technical_terms:
                allow.write("\n".join(technical_terms) + "\n")
                allow.flush()
                argv += ["--allow:file", allow.name]
            try:
                proc = subprocess.run(
                    argv,
                    input=text,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=self.timeout_s,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return Skipped(f"error: timeout {self.timeout_s}s")
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1:] or [""]
            return Skipped(f"error: exit {proc.returncode}: {tail[0]}")
        return parse_report(json.loads(proc.stdout))


def checker_off(text: str, technical_terms: tuple[str, ...]) -> CheckerOutcome:
    return Skipped("off")
