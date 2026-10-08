"""Verify the artifacts under data/ against the manifest, each other, and
the PDF. Necessary, not sufficient: a pass means none of the checks below
found a defect, not that the data is a faithful copy of the spec.

Run: uv run scripts/verify.py    exit 0 all checks pass, 1 any failure

Checks:
- manifest: it lists exactly the artifacts in data/, and each digest and
  byte size matches the file
- every artifact: schema_version and the source block, PDF digest included
- dictionary: approved iff the headword is uppercase; key (word, pos,
  qualifier) unique; pos from the closed set
- examples: no "Blank Page" text; each STE example word with a lowercase
  letter is a unit, "No.", or a list label such as "(a)", so a Non-STE
  word that crosses the column split fails
- lexicon: approved words are the dictionary's uppercase headwords
  lowercased, with lowercase forms; ids unique; each unapproved entry
  carries the dictionary's help, and one with no alternative has help
- referential integrity: every alternative in the lexicon names an
  approved id; every tagged alternative of an approved dictionary entry
  resolves the same way
- approved verbs: equal to the spec's own "List of approved verbs"
- rules: ids unique and equal to the PDF's rule list; each checked
  parameter equals the number the spec states; the approved -ing words
  are approved lexicon entries
- counts: reported against the spec's 875 approved, 1274 not approved

Not checked (record of the gaps):
- meaning, help, and example text: only that it was assigned, not that
  the column split or the help-indent threshold put each line right
- alternative context strings and phrase alternatives (phrases may hold
  technical nouns, so their words are counted, not required)
- derived noun plurals: regular rules only; uncountable and irregular
  nouns get a wrong or needless plural
- completeness of entries other than verbs: no independent list exists
  in the PDF for the other parts of speech
- rule paraphrases and every parameter of a judgment rule
"""

import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterator
from typing import Any

import pymupdf

import extract_dictionary
import extract_rules
import spec

SPEC_APPROVED, SPEC_UNAPPROVED = 875, 1274
POS_CLOSED = frozenset(extract_dictionary.POS_TAGS)
NUMBER_WORDS = {"one": 1, "three": 3, "four": 4, "six": 6, "twenty-two": 22}

Failures = list[str]


def load(name: str) -> tuple[bytes, dict[str, Any]]:
    blob = (spec.DATA / name).read_bytes()
    return blob, json.loads(blob)


# ---- checks: each returns the failures it found ----------------------------


def check_manifest(manifest: dict[str, Any]) -> Failures:
    out = []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    present = {f"data/{p.name}" for p in spec.DATA.glob("*.json") if p.name != "manifest.json"}
    if set(listed) != present:
        out.append(f"manifest lists {sorted(listed)}, data/ holds {sorted(present)}")
    for path, a in listed.items():
        blob = (spec.ROOT / path).read_bytes() if (spec.ROOT / path).exists() else b""
        if spec.sha256(blob) != a["sha256"] or len(blob) != a["bytes"]:
            out.append(f"{path}: digest or size differs from manifest")
    return out


def check_header(name: str, doc: dict[str, Any], source: dict[str, Any]) -> Failures:
    out = []
    if doc.get("schema_version") != spec.SCHEMA_VERSION:
        out.append(f"{name}: schema_version {doc.get('schema_version')!r}")
    if doc.get("source") != source:
        out.append(f"{name}: source block differs from the PDF in artifacts/")
    return out


def check_dictionary(entries: list[dict[str, Any]]) -> Failures:
    out = []
    keys = Counter((e["word"], e["pos"], e["qualifier"]) for e in entries)
    out += [f"duplicate key {k}" for k, n in keys.items() if n > 1]
    for e in entries:
        upper = extract_dictionary.is_approved(e["word"])
        if upper != (e["status"]["kind"] == "approved"):
            out.append(f"{e['word']!r}: status {e['status']['kind']} but case says otherwise")
        pos = e["pos"]
        if pos == "prefix" and not e["word"].endswith("-"):
            out.append(f"{e['word']!r}: pos prefix on a word that is not a prefix")
        elif pos is not None and pos != "prefix" and pos not in POS_CLOSED:
            out.append(f"{e['word']!r}: pos {pos!r} outside the closed set")
    return out


def check_lexicon(entries: list[dict[str, Any]], lexicon: dict[str, Any]) -> Failures:
    out = []
    upper = [e for e in entries if e["status"]["kind"] == "approved"]
    want = Counter((e["word"].lower(), e["pos"]) for e in upper)
    have = Counter((a["word"], a["pos"]) for a in lexicon["approved"])
    if want != have:
        out.append(
            f"lexicon approved set differs from dictionary: {sorted(((want - have) + (have - want)).elements())[:5]}"
        )
    ids = Counter(a["id"] for a in lexicon["approved"])
    out += [f"duplicate lexicon id {i!r}" for i, n in ids.items() if n > 1]
    for a in lexicon["approved"]:
        bad = [f for f in [a["word"], *a["forms"]] if f != f.lower()]
        out += [f"lexicon form {f!r} not lowercase" for f in bad]
    helps = {
        (e["word"].lower(), e["pos"], e["qualifier"]): e["status"]["help"]
        for e in entries
        if e["status"]["kind"] == "unapproved"
    }
    for u in lexicon["unapproved"]:
        key = (u["word"], u["pos"], u["qualifier"])
        if u.get("help") != helps.get(key):
            out.append(f"lexicon help of {key!r} differs from the dictionary")
        if not u["alternatives"] and not u.get("help"):
            out.append(f"lexicon {key!r}: no alternative and no help, a dead end")
    return out


def check_references(entries: list[dict[str, Any]], lexicon: dict[str, Any]) -> Failures:
    out = []
    ids = {a["id"] for a in lexicon["approved"]}
    for u in lexicon["unapproved"]:
        for alt in u["alternatives"]:
            if "unresolved" in alt:
                out.append(
                    f"{u['word']!r}: alternative {alt['unresolved']!r} names no approved word"
                )
            elif "ref" in alt and alt["ref"] not in ids:
                out.append(f"{u['word']!r}: ref {alt['ref']!r} is not an approved id")
    index = extract_dictionary.Index.of(lexicon["approved"])
    for e in entries:
        if e["status"]["kind"] != "approved":
            continue
        for alt in e["status"]["alternatives"]:
            r = index.resolve(alt)
            if "unresolved" in r or ("ref" in r and r["ref"] not in ids):
                out.append(f"{e['word']!r}: other-meaning alternative {alt} does not resolve")
    return out


def approved_verb_list(pdf: pymupdf.Document) -> set[str]:
    """The spec's own list: 10 pt plain text on the 'List of approved verbs'
    page(s); the bold single letters are section markers."""
    out: set[str] = set()
    for page in pdf:
        text = page.get_text()
        if "List of approved verbs" not in text or "Page 2-0-" not in text:
            continue  # the Highlights also name the list
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for s in line["spans"]:
                    if s["size"] < 10.5 and "Bold" not in s["font"] and s["text"].strip():
                        out.add(s["text"].strip())
    return out


def check_verbs(entries: list[dict[str, Any]], listed: set[str]) -> Failures:
    ours = {e["word"] for e in entries if e["status"]["kind"] == "approved" and e["pos"] == "v"}
    if not listed:
        return ["no 'List of approved verbs' found in the PDF"]
    if ours != listed:
        return [
            f"approved verbs differ: only in list {sorted(listed - ours)}, only parsed {sorted(ours - listed)}"
        ]
    return []


def part1_text(pdf: pymupdf.Document) -> str:
    """Part 1 as one string, whitespace collapsed."""
    pages = (p.get_text() for p in pdf if extract_rules.PART1_LABEL.search(p.get_text()))
    return " ".join(" ".join(pages).split())


def number(word: str) -> int:
    return int(word) if word.isdigit() else NUMBER_WORDS[word]


# (rule id, parameter getter, pattern over a scope, scope) - each pattern
# captures the number the spec states for that parameter.
Param = tuple[str, Callable[[dict[str, Any]], Any], str, str]
PARAMS: tuple[Param, ...] = (
    ("5.1", lambda p: p["max_words_per_sentence"], r"maximum of (\d+) words", "statement"),
    ("6.3", lambda p: p["max_words_per_sentence"], r"maximum of (\d+) words", "statement"),
    ("6.6", lambda p: p["max_sentences_per_paragraph"], r"more than (\w+) sentences", "statement"),
    ("2.1", lambda p: p["max_words_in_multi_word_noun"], r"no more than (\w+) words", "statement"),
    ("2.2", lambda p: p["max_words_in_multi_word_noun"], r"more than (\w+) words", "statement"),
    (
        "5.1",
        lambda p: p["notes_max_words_per_sentence"],
        r"sentence in a note is (\d+) words",
        "part1",
    ),
    (
        "8.5",
        lambda p: p["parenthetical_counts_as_words"],
        r"counts as (one) word in that sentence",
        "statement",
    ),
    ("8.7", lambda p: p["hyphenated_counts_as_words"], r"count as (one) word", "statement"),
    (
        "1.5",
        lambda p: len(p["technical_noun_categories"]),
        r"one or more of these ([\w-]+) categories",
        "part1:1.5",
    ),
    (
        "1.12",
        lambda p: len(p["technical_verb_categories"]),
        r"one or more of these ([\w-]+) categories",
        "part1:1.12",
    ),
)


def check_rules(
    rules: list[dict[str, Any]], listed: list[extract_rules.Listed], part1: str
) -> Failures:
    out = []
    ids = [r["id"] for r in rules]
    if len(set(ids)) != len(ids):
        out.append("duplicate rule ids")
    if ids != [r.id for r in listed]:
        out.append("rule ids differ from the PDF's rule list")
    by_id = {r["id"]: r for r in rules}
    statements = {r.id: r.statement for r in listed}
    for rule_id, get, pattern, scope in PARAMS:
        if scope == "statement":
            text = statements[rule_id]
        elif scope.startswith("part1:"):
            # the text after this rule's heading in the body, up to the next rule
            start = part1.find(f"Rule {scope[6:]} ")
            start = part1.find(f"Rule {scope[6:]} ", start + 1)
            text = part1[start : start + 6000]
        else:
            text = part1
        m = re.search(pattern, text)
        stated = number(m.group(1)) if m else None
        value = get(by_id[rule_id]["parameters"])
        if stated != value:
            out.append(f"rule {rule_id}: parameter {value!r}, spec states {stated!r}")
    if (
        ";" not in by_id["8.1"]["parameters"]["forbidden_punctuation"]
        or "semicolon (;)" not in statements["8.1"]
    ):
        out.append("rule 8.1: semicolon ban not stated or not recorded")
    return out


def check_ing(rules: list[dict[str, Any]], lexicon: dict[str, Any], part1: str) -> Failures:
    ing = next(r for r in rules if r["id"] == "3.5")["parameters"]["ing_approved"]
    ids = {a["id"] for a in lexicon["approved"]}
    out = [f"rule 3.5: {i!r} is not an approved lexicon entry" for i in ing if i not in ids]
    section = part1[part1.find("Approved words that have an “-ing” form") :][:600]
    out += [
        f"rule 3.5: {i!r} not named in the spec's list" for i in ing if i.split()[0] not in section
    ]
    return out


def counts(entries: list[dict[str, Any]]) -> Iterator[str]:
    appr = [e for e in entries if e["status"]["kind"] == "approved"]
    unappr = [e for e in entries if e["status"]["kind"] == "unapproved"]
    yield f"entries {len(entries)} (spec {SPEC_APPROVED + SPEC_UNAPPROVED})"
    for name, group, stated in (
        ("approved", appr, SPEC_APPROVED),
        ("not approved", unappr, SPEC_UNAPPROVED),
    ):
        keys = len({(e["word"], e["pos"], e["qualifier"]) for e in group})
        words = len({e["word"].lower() for e in group})
        yield f"{name}: {keys} by (word, pos, qualifier), {words} distinct words; spec states {stated}"
    untagged = [e["word"] for e in entries if e["pos"] is None]
    yield f"headwords the spec prints with no part of speech: {untagged}"


# Lowercase is legal in an STE example only in these words of Issue 9.
LOWER = re.compile(r"[a-z]")
STE_LOWER = re.compile(r"\(?(?:mm|ml|kPa|bar|mbar|psi|MHz|Hz|kg|Nm|lb|in|µm|No|[a-z])[).,]*")


def check_examples(entries: list[dict[str, Any]]) -> Failures:
    out = []
    for e in entries:
        texts = [t for t in (e["ste_example"], e["nonste_example"]) if t]
        if any("Blank Page" in t for t in texts):
            out.append(f"{e['word']!r}: example holds 'Blank Page'")
        stray = [
            w
            for w in (e["ste_example"] or "").split()
            if LOWER.search(w) and not STE_LOWER.fullmatch(w)
        ]
        if stray:
            out.append(f"{e['word']!r}: STE example has lowercase words {stray}")
    return out


def main() -> int:
    failures: Failures = []
    _, manifest = load("manifest.json")
    failures += check_manifest(manifest)
    source = spec.source()
    docs = {n: load(n)[1] for n in ("dictionary.json", "lexicon.json", "rules.json")}
    for name, doc in [("manifest.json", manifest), *docs.items()]:
        failures += check_header(name, doc, source)
    entries, lexicon, rules = (
        docs["dictionary.json"]["entries"],
        docs["lexicon.json"],
        docs["rules.json"]["rules"],
    )
    pdf = pymupdf.open(spec.PDF)
    part1 = part1_text(pdf)
    failures += check_dictionary(entries)
    failures += check_examples(entries)
    failures += check_lexicon(entries, lexicon)
    failures += check_references(entries, lexicon)
    failures += check_verbs(entries, approved_verb_list(pdf))
    failures += check_rules(rules, extract_rules.listed_rules(pdf), part1)
    failures += check_ing(rules, lexicon, part1)
    for line in counts(entries):
        print(f"COUNT {line}")
    mismatched = [
        (u["word"], a)
        for u in lexicon["unapproved"]
        for a in u["alternatives"]
        if "stated_pos" in a
    ]
    print(f"NOTE alternatives whose stated pos differs from the approved entry: {mismatched}")
    phrases = [
        a["phrase"] for u in lexicon["unapproved"] for a in u["alternatives"] if "phrase" in a
    ]
    forms = {f for a in lexicon["approved"] for f in a["forms"]}
    outside = sorted({w for p in phrases for w in p.split() if w not in forms})
    print(f"NOTE words in phrase alternatives outside the lexicon: {outside}")
    for f in failures:
        print(f"FAIL {f}")
    print(f"{'FAIL' if failures else 'PASS'}: {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
