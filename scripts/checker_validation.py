"""Validate the asd-ste100 checker on the spec's own examples.

Run: uv run scripts/checker_validation.py [--skill PATH | --command CMD]
       [--jobs N] [--probe N] [--reuse] [--limit N]

PATH is the asd-ste100 skill root (the directory with SKILL.md); default
the vendored copy at .github/skills/asd-ste100. CMD replaces the skill
binding, for checker code not yet released.

Oracle: data/dictionary.json. Each entry has an STE example (capitals)
and, for most, a Non-STE example (sentence case) that uses the headword.
- STE example: each finding is a false positive. A finding on a word with
  no dictionary entry is the allow list's miss, and one on a word whose
  only entries are unapproved non-nouns (FUEL, PUMP) is a homograph; both
  are reported apart from the checker-owned rest.
- Non-STE example of an unapproved headword: the checker must flag the
  headword. Not scored: approved headwords and unapproved entries whose
  word and pos also have an approved entry (GET (v) / get (v)); their
  Non-STE example differs in meaning only (rule 1.3, outside the checker).

Allow list: each token of the STE examples that `lookup` does not find, in
the STE examples of two or more entries, and no -s or -ed form of a
headword. One `lookup` call. Bias: optimistic on the STE side, since the
list comes from the same examples; a technical noun in one example stays a
finding.

Probe: N STE examples (each k-th entry) also go to the checker in sentence
case. A finding or signal set that changes is a case effect.

Each text is one `check --text:stdin --mode description` process: the
skill documents no batch call. Output: markdown on stdout; per-example
detail and raw reports in eval/results/checker-validation.TAG.*, TAG a
digest of the checker command. --reuse reads the raw reports when the
command, allow list, and texts are equal. Exit 0 on a completed run, 1 on
a checker error.
"""

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parent.parent
DICTIONARY = REPO / "data" / "dictionary.json"
RESULTS = REPO / "eval" / "results"
DEFAULT_SKILL = REPO / ".github" / "skills" / "asd-ste100"

Side = Literal["ste", "nonste", "probe"]
Hit = Literal["finding", "inflected", "signal", "miss"]
# A not_approved token, by what the dictionary holds for it:
# - unknown: no entry; a technical noun the allow list missed
# - homograph: unapproved entries only, and either none a noun ("fuel
#   (v)") or one that names the word as a technical noun ("support (n)":
#   SUPPORT (TN)); the spec's own examples use these as technical nouns
# - dictionary: any other entry; the checker and the spec disagree
Origin = Literal["unknown", "homograph", "dictionary", ""]
# Per entry: pos, approved, and whether its alternatives name the word
# itself as a technical noun ("support (n)": use "support (TN)").
Senses = frozenset[tuple[str | None, bool, bool]]

# A word: letters, then letters, apostrophes, or inner hyphens. Numbers and
# marks are not words. One class per quantifier, so the scan is linear.
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")
SENTENCE_START = re.compile(r"(^|[.!?:]\s+|\(\w\)\s+)([a-z])")


# ---- domain ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Entry:
    word: str
    pos: str | None
    qualifier: str | None
    approved: bool
    meaning_only: bool  # unapproved, but the same word and pos is approved
    forms: tuple[str, ...]
    ste: str
    nonste: str | None

    @property
    def key(self) -> str:
        q = f" [{self.qualifier}]" if self.qualifier else ""
        return f"{self.word} ({self.pos}){q}"

    @property
    def targets(self) -> frozenset[str]:
        """Lowercase words and phrases that name the headword in a finding:
        the headword, its forms, each of their words, and the qualified
        phrase ("few", "a few")."""
        whole = [self.word, *self.forms, *([self.qualifier] if self.qualifier else [])]
        words = (w for p in whole for w in p.split())
        return frozenset(x.lower() for x in (*whole, *words))


def parse_entries(raw: Sequence[dict[str, Any]]) -> list[Entry]:
    """Entries with an STE example (only `re-` lacks one)."""
    approved = {
        (r["word"].lower(), r["pos"]) for r in raw if r["status"]["kind"] == "approved"
    }
    return [
        Entry(
            word=r["word"],
            pos=r["pos"],
            qualifier=r["qualifier"],
            approved=r["status"]["kind"] == "approved",
            meaning_only=r["status"]["kind"] == "unapproved"
            and (r["word"].lower(), r["pos"]) in approved,
            forms=tuple(r["forms"]),
            ste=r["ste_example"],
            nonste=r["nonste_example"],
        )
        for r in raw
        if r["ste_example"]
    ]


ENDINGS = (("ies", "y"), ("ied", "y"), ("es", ""), ("ed", ""))


def bases(word: str, ing: bool = True) -> tuple[str, ...]:
    """The word and the stems of its regular endings: -s, -es, -ies, -ed,
    and -ing unless `ing` is false. Over-generates; used only to match a
    token to a headword."""
    w = word.lower()
    out = [w]
    for end, add in (*ENDINGS, *((("ing", ""),) if ing else ())):
        if w.endswith(end) and len(w) > len(end) + 2:
            out += [w[: -len(end)] + add, w[: -len(end)] + "e"]
    if w.endswith(("s", "d")):
        out.append(w[:-1])
    return tuple(dict.fromkeys(out))


@dataclass(frozen=True, slots=True)
class Item:
    """One finding or signal, reduced to what two reports can compare."""

    group: Literal["finding", "signal"]
    kind: str
    token: str  # lowercase; "" for a kind with no word (length, mark)
    headword: str  # lowercase checker headword, or ""
    origin: Origin  # for not_approved only


@dataclass(frozen=True, slots=True)
class Run:
    side: Side
    entry: Entry
    text: str
    items: tuple[Item, ...]
    seconds: float

    def findings(self) -> list[Item]:
        return [i for i in self.items if i.group == "finding"]

    def signals(self) -> list[Item]:
        return [i for i in self.items if i.group == "signal"]


def sentence_case(text: str) -> str:
    """'THE PUMP IS ON. OPEN IT.' -> 'The pump is on. Open it.'"""
    return SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).upper(), text.lower())


def words_of(text: str) -> Iterator[str]:
    return (m.group(0) for m in WORD.finditer(text))


def allow_candidates(entries: Sequence[Entry]) -> Counter[str]:
    """Token (uppercase) -> number of entries whose STE example holds it."""
    return Counter(w for e in entries for w in set(words_of(e.ste.upper())))


def allow_list(
    counts: Counter[str], lexicon: dict[str, Senses], headwords: frozenset[str]
) -> list[str]:
    """Unknown to lookup, in two or more entries, and no -s or -ed form of a
    headword ("SPARKS" stays out: spark (v) is a headword). An -ing word may
    stay: the spec permits -ing in a technical noun (WIRING, PARKING)."""
    return sorted(
        w
        for w, n in counts.items()
        if n >= 2
        and not lexicon.get(w.lower())
        and not any(b in headwords for b in bases(w, ing=False))
    )


def hit_of(entry: Entry, run: Run) -> Hit:
    """How the Non-STE report names the entry's headword, best first."""
    t = entry.targets
    found = run.findings()
    if any(
        i.kind == "not_approved" and (i.token in t or i.headword in t) for i in found
    ):
        return "finding"
    first = entry.word.lower().split()[0]
    stem = first[: max(3, len(first) - 2)]
    if any(
        i.kind in ("not_approved", "ing_form") and i.token.startswith(stem)
        for i in found
    ):
        return "inflected"
    if any(b in t for i in run.signals() for b in bases(i.token)):
        return "signal"
    return "miss"


def origin_of(senses: Senses | None) -> Origin:
    if not senses:
        return "unknown"
    if any(ok for _, ok, _ in senses):
        return "dictionary"
    if any(tn for _, _, tn in senses) or not any(pos == "n" for pos, _, _ in senses):
        return "homograph"
    return "dictionary"


def items_of(report: dict[str, Any], lexicon: dict[str, Senses]) -> tuple[Item, ...]:
    def one(group: Literal["finding", "signal"], f: dict[str, Any]) -> Item:
        token = str(f.get("token") or f.get("mark") or "").lower()
        origin = origin_of(lexicon.get(token)) if f["kind"] == "not_approved" else ""
        return Item(
            group, f["kind"], token, str(f.get("headword") or "").lower(), origin
        )

    return (
        *(one("finding", f) for f in report["findings"]),
        *(one("signal", s) for s in report["signals"]),
    )


# ---- shell: the checker ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class Checker:
    argv: tuple[str, ...]  # the bound command, as SKILL.md binds it

    @classmethod
    def of(cls, command: str) -> "Checker":
        """An explicit command, such as an unreleased checker's entry point."""
        return cls(tuple(shlex.split(command)))

    @classmethod
    def at(cls, skill: Path) -> "Checker":
        scripts = (skill / "scripts").resolve()
        if not (scripts / "pyproject.toml").is_file():
            raise SystemExit(f"ERROR no asd-ste100 scripts at {scripts}; pass --skill")
        uv = shutil.which("uv") or "uv"
        # The SKILL.md binding unsets VIRTUAL_ENV. UV_PROJECT_ENVIRONMENT
        # must go too: inherited, it makes uv install the skill into the
        # caller's environment (here, ste-tax's .venv).
        unset = ("-u", "VIRTUAL_ENV", "-u", "UV_PROJECT_ENVIRONMENT")
        return cls(
            ("env", *unset, uv, "run", "--project", str(scripts), "btm-asd-ste100")
        )

    def call(self, *args: str, stdin: str | None = None) -> dict[str, Any]:
        p = subprocess.run(
            [*self.argv, *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise RuntimeError(
                f"checker exit {p.returncode} on {args}: {p.stderr[-400:]}"
            )
        doc: dict[str, Any] = json.loads(p.stdout)
        return doc

    def check(self, text: str, allow: Path) -> tuple[dict[str, Any], float]:
        t0 = time.perf_counter()
        doc = self.call(
            "check",
            "--text:stdin",
            "--mode",
            "description",
            "--allow:file",
            str(allow),
            stdin=text,
        )
        return doc, time.perf_counter() - t0

    def lookup(self, words: Iterable[str]) -> tuple[dict[str, Senses], str]:
        """Lowercase word -> senses of each entry; release tag."""
        doc = self.call("lookup", *sorted(set(words)))
        senses = {
            w["word"].lower(): frozenset(
                (
                    e.get("pos"),
                    e["status"]["kind"] == "approved",
                    f"{e['word'].lower()} (tn)"
                    in map(str.lower, e.get("alternatives", [])),
                )
                for e in w["entries"]
            )
            for w in doc["words"]
        }
        return senses, doc["version"]


# ---- core: tables ---------------------------------------------------------


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "n/a"


def table(head: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def kind_label(i: Item) -> str:
    return f"not_approved ({i.origin})" if i.kind == "not_approved" else i.kind


def blamed(i: Item) -> bool:
    """A finding the checker owns: not a technical noun it could not know."""
    return i.group == "finding" and (
        i.kind != "not_approved" or i.origin == "dictionary"
    )


FORM_KINDS = frozenset(
    ["contraction", "punctuation", "sentence_length", "paragraph_length"]
)


def attested(ste: Sequence[Run]) -> frozenset[str]:
    """H: homograph tokens in the findings of two or more STE examples."""
    seen = Counter(
        t for r in ste for t in {i.token for i in r.items if i.origin == "homograph"}
    )
    return frozenset(t for t, n in seen.items() if n >= 2)


def gate_table(ste: Sequence[Run], scored: Sequence[Run]) -> str:
    """Candidate gates: which findings reject a text. For each gate, the
    STE examples it rejects (false rejects) and the scored Non-STE
    examples whose headword it catches as a finding (recall).

    H: homograph tokens in the findings of two or more STE examples (FUEL,
    PUMP): the spec itself uses them as technical nouns. In-sample, so the
    rows that drop H are optimistic for the STE side."""
    h = attested(ste)
    gates: list[tuple[str, Callable[[Item], bool]]] = [
        ("every finding (`ok`)", lambda i: True),
        ("every finding but unknown words", lambda i: i.origin != "unknown"),
        (
            f"every finding but unknown words and H ({len(h)} tokens)",
            lambda i: i.origin != "unknown" and i.token not in h,
        ),
        (
            "every finding but unknown words, H, and ing_form",
            lambda i: (
                i.origin != "unknown" and i.token not in h and i.kind != "ing_form"
            ),
        ),
        ("form only: contraction, `;`, length", lambda i: i.kind in FORM_KINDS),
    ]
    found = ("finding", "inflected")

    def keep(r: Run, gate: Callable[[Item], bool]) -> Run:
        return replace(
            r, items=tuple(i for i in r.items if i.group == "signal" or gate(i))
        )

    rows = []
    for name, gate in gates:
        rejected = sum(1 for r in ste if keep(r, gate).findings())
        caught = sum(1 for r in scored if hit_of(r.entry, keep(r, gate)) in found)
        rows.append(
            (
                name,
                f"{rejected} ({pct(rejected, len(ste))})",
                f"{caught} ({pct(caught, len(scored))})",
            )
        )
    return table(("gate", "STE examples rejected", "Non-STE headword caught"), rows)


def report(runs: Sequence[Run], allow: Sequence[str], version: str, jobs: int) -> str:
    ste = [r for r in runs if r.side == "ste"]
    non = [r for r in runs if r.side == "nonste"]
    probe = [r for r in runs if r.side == "probe"]
    scored = [r for r in non if not r.entry.approved and not r.entry.meaning_only]
    meaning = [r for r in non if r.entry.approved or r.entry.meaning_only]
    out = [f"checker {version}; {len(runs)} check calls; allow list {len(allow)} terms"]
    secs = [r.seconds for r in runs]
    out.append(
        f"per call {sum(secs) / len(secs):.3f} s mean, {max(secs):.3f} s max; "
        f"{jobs} parallel jobs"
    )

    # STE side: false positives.
    out.append("\n## STE examples: false positives\n")
    kinds = Counter(kind_label(i) for r in ste for i in r.items)
    with_any = Counter(k for r in ste for k in {kind_label(i) for i in r.items})
    out.append(
        table(
            ("kind", "group", "items", "per example", "examples with one or more"),
            (
                (
                    k,
                    g,
                    kinds[k],
                    f"{kinds[k] / len(ste):.3f}",
                    f"{with_any[k]} ({pct(with_any[k], len(ste))})",
                )
                for g, k in sorted(
                    {(i.group, kind_label(i)) for r in ste for i in r.items}
                )
            ),
        )
    )
    dict_fp = [r for r in ste if any(map(blamed, r.items))]
    homo = [r for r in ste if any(i.origin == "homograph" for i in r.items)]
    dict_ids = {id(r) for r in dict_fp}
    any_fp = [r for r in ste if r.findings()]
    out.append(
        f"\nSTE examples: {len(ste)}. With any finding: {len(any_fp)} ({pct(len(any_fp), len(ste))}). "
        f"With a homograph finding (technical noun spelled as an unapproved headword): {len(homo)} "
        f"({pct(len(homo), len(ste))}). With a checker-owned finding (origin dictionary, or "
        f"a kind other than not_approved): {len(dict_fp)} ({pct(len(dict_fp), len(ste))})."
    )

    tok = Counter((i.kind, i.token) for r in ste for i in r.items if blamed(i))
    out.append("\nMost frequent checker-owned STE findings:\n")
    out.append(
        table(
            ("kind", "token", "examples"),
            ((k, t, n) for (k, t), n in tok.most_common(30)),
        )
    )

    ht = Counter(i.token for r in ste for i in r.items if i.origin == "homograph")
    out.append("\nMost frequent homograph tokens on the STE side:\n")
    out.append(table(("token", "examples"), ht.most_common(20)))

    # Non-STE side: recall of the headword.
    out.append("\n## Non-STE examples: headword recall\n")
    hits = {id(r): hit_of(r.entry, r) for r in scored}
    hc = Counter(hits.values())
    out.append(
        table(
            ("outcome", "examples", "share"),
            (
                (h, hc[h], pct(hc[h], len(scored)))
                for h in ("finding", "inflected", "signal", "miss")
            ),
        )
    )
    out.append(
        f"\nScored: {len(scored)} unapproved headwords. Recall as a finding: "
        f"{pct(hc['finding'] + hc['inflected'], len(scored))}; with signals: "
        f"{pct(len(scored) - hc['miss'], len(scored))}."
    )
    mh = Counter(hit_of(r.entry, r) for r in meaning)
    out.append(
        f"Not scored: {len(meaning)} Non-STE examples of a meaning the checker "
        f"cannot see (approved headword, or unapproved with the same word and "
        f"pos approved); finding {mh['finding']}, inflected {mh['inflected']}, "
        f"signal {mh['signal']}, miss {mh['miss']}."
    )
    out.append("\n## Gate options\n")
    out.append(gate_table(ste, scored))
    out.append("")
    multi = [r for r in scored if " " in r.entry.word or r.entry.qualifier]
    mc = Counter(hits[id(r)] for r in multi)
    out.append(
        f"Multi-word or qualified headwords: {len(multi)}; finding {mc['finding']}, "
        f"inflected {mc['inflected']}, signal {mc['signal']}, miss {mc['miss']}."
    )

    out.append("\n## Confusion by part of speech\n")
    by_pos: dict[str, list[Run]] = defaultdict(list)
    for r in ste:
        by_pos[str(r.entry.pos)].append(r)
    hit_pos: dict[str, Counter[str]] = defaultdict(Counter)
    for r in scored:
        hit_pos[str(r.entry.pos)][hits[id(r)]] += 1
    out.append(
        table(
            (
                "pos",
                "STE examples",
                "STE with dictionary finding",
                "Non-STE scored",
                "finding",
                "inflected",
                "signal",
                "miss",
                "recall",
            ),
            (
                (
                    p,
                    len(rs),
                    pct(sum(1 for r in rs if id(r) in dict_ids), len(rs)),
                    sum(hit_pos[p].values()),
                    hit_pos[p]["finding"],
                    hit_pos[p]["inflected"],
                    hit_pos[p]["signal"],
                    hit_pos[p]["miss"],
                    pct(
                        hit_pos[p]["finding"] + hit_pos[p]["inflected"],
                        sum(hit_pos[p].values()),
                    ),
                )
                for p, rs in sorted(by_pos.items(), key=lambda kv: -len(kv[1]))
            ),
        )
    )

    out.append("\n## Confusion by finding kind\n")
    nk = Counter(k for r in non for k in {kind_label(i) for i in r.items})
    sk = with_any
    out.append(
        table(
            ("kind", "STE examples with it", "Non-STE examples with it"),
            (
                (
                    k,
                    f"{sk[k]} ({pct(sk[k], len(ste))})",
                    f"{nk[k]} ({pct(nk[k], len(non))})",
                )
                for k in sorted(set(sk) | set(nk))
            ),
        )
    )

    out.append("\n## Worst STE offenders\n")
    worst = sorted(
        dict_fp,
        key=lambda r: -sum(map(blamed, r.items)),
    )[:20]
    out.append(
        table(
            ("entry", "findings", "text"),
            (
                (
                    r.entry.key,
                    ", ".join(f"{i.kind}:{i.token}" for i in r.items if blamed(i)),
                    r.text,
                )
                for r in worst
            ),
        )
    )

    out.append("\n## Non-STE misses\n")
    misses = [r for r in scored if hits[id(r)] == "miss"]
    out.append(
        table(
            ("entry", "flagged", "text"),
            (
                (
                    r.entry.key,
                    ", ".join(sorted({i.token for i in r.findings() if i.token})),
                    r.text,
                )
                for r in misses
            ),
        )
    )

    out.append("\n## Probe: capitals and sentence case\n")
    base = {r.entry.key: r for r in ste}
    diffs = []
    for r in probe:
        a = Counter((i.group, i.kind, i.token) for i in base[r.entry.key].items)
        b = Counter((i.group, i.kind, i.token) for i in r.items)
        if a != b:
            diffs.append(
                (r.entry.key, sorted((a - b).elements()), sorted((b - a).elements()))
            )
    out.append(
        f"Probed {len(probe)} STE examples; reports differ on {len(diffs)} ({pct(len(diffs), len(probe))}).\n"
    )
    dk = Counter(
        (side, g, k)
        for _, only_caps, only_sent in diffs
        for side, items in (
            ("capitals only", only_caps),
            ("sentence case only", only_sent),
        )
        for g, k, _t in items
    )
    out.append(
        table(
            ("present in", "group", "kind", "items"),
            ((s, g, k, n) for (s, g, k), n in dk.most_common()),
        )
    )
    out.append("")
    out.append(
        table(
            ("entry", "capitals only", "sentence case only"),
            (
                (
                    k,
                    "; ".join(f"{x[1]}:{x[2]}" for x in a),
                    "; ".join(f"{x[1]}:{x[2]}" for x in b),
                )
                for k, a, b in diffs[:25]
            ),
        )
    )
    return "\n".join(out)


def detail(runs: Sequence[Run], allow: Sequence[str], version: str) -> dict[str, Any]:
    return {
        "checker": version,
        "allow": list(allow),
        "h": sorted(attested([r for r in runs if r.side == "ste"])),
        "runs": [
            {
                "side": r.side,
                "entry": r.entry.key,
                "text": r.text,
                "seconds": round(r.seconds, 3),
                "items": [
                    {
                        "group": i.group,
                        "kind": i.kind,
                        "token": i.token,
                        "origin": i.origin,
                    }
                    for i in r.items
                ],
            }
            for r in runs
        ],
    }


# ---- shell: main ----------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", type=Path, default=DEFAULT_SKILL)
    ap.add_argument(
        "--command",
        help="checker command in place of the skill binding (unreleased code)",
    )
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument(
        "--reuse",
        action="store_true",
        help="reuse the saved reports when checker, allow list, and texts are equal",
    )
    ap.add_argument(
        "--probe", type=int, default=300, help="STE examples to probe in sentence case"
    )
    ap.add_argument(
        "--limit", type=int, default=None, help="first N entries only (smoke test)"
    )
    args = ap.parse_args(argv)

    raw = json.loads(DICTIONARY.read_text())["entries"]
    entries = parse_entries(raw)[: args.limit]
    checker = Checker.of(args.command) if args.command else Checker.at(args.skill)

    counts = allow_candidates(entries)
    headwords = frozenset(t for e in entries for t in e.targets)
    lexicon, version = checker.lookup(counts)
    allow = allow_list(counts, lexicon, headwords)

    stride = max(1, len(entries) // max(1, args.probe))
    jobs: list[tuple[Side, Entry, str]] = [
        *(("ste", e, e.ste) for e in entries),
        *(("nonste", e, e.nonste) for e in entries if e.nonste),
        *(("probe", e, sentence_case(e.ste)) for e in entries[::stride][: args.probe]),
    ]

    RESULTS.mkdir(parents=True, exist_ok=True)
    allow_path = RESULTS / "checker-validation.allow.txt"
    allow_path.write_text("\n".join(allow) + "\n")

    key = {"argv": list(checker.argv), "allow": allow, "texts": [j[2] for j in jobs]}
    tag = hashlib.sha256(" ".join(checker.argv).encode()).hexdigest()[:8]
    raw_path = RESULTS / f"checker-validation.{tag}.reports.json"  # for --reuse
    cached = (
        json.loads(raw_path.read_text()) if args.reuse and raw_path.is_file() else {}
    )
    if cached.get("key") == key:
        reports = [(doc, secs) for doc, secs in cached["reports"]]
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            reports = list(pool.map(lambda j: checker.check(j[2], allow_path), jobs))
        raw_path.write_text(json.dumps({"key": key, "reports": reports}))

    # A token a report names but the allow-list lookup never saw.
    seen = {
        str(f.get("token", "")).lower()
        for doc, _ in reports
        for f in doc["findings"] + doc["signals"]
    }
    fresh = [
        w for w in seen - set(lexicon) if w and all(map(WORD.fullmatch, w.split()))
    ]
    if fresh:
        lexicon |= checker.lookup(fresh)[0]

    runs = [
        Run(side, e, text, items_of(doc, lexicon), secs)
        for (side, e, text), (doc, secs) in zip(jobs, reports, strict=True)
    ]
    out = RESULTS / f"checker-validation.{tag}.json"
    out.write_text(json.dumps(detail(runs, allow, version), indent=1) + "\n")
    print(report(runs, allow, version, args.jobs))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as err:
        print(f"ERROR {err}", file=sys.stderr)
        sys.exit(1)
