#!/usr/bin/env python3
"""Decode the ASD-STE100 Part 2 dictionary into typed JSONL records.

Input: artifacts/ASD-STE100_ISSUE9.pdf (educational-use grant, see LICENSE).
Output: data/ste100_dictionary.jsonl, one record per headword variant.

Record:
  {"word": str, "pos": str, "qualifier": str|null, "forms": [str],
   "status": {"kind": "approved", "meaning": str}
           | {"kind": "unapproved", "guidance": str},
   "ste_example": str|null, "nonste_example": str|null}

Enforced (fields cannot contradict):
- Approval = headword case only. No stored bool; is_approved() derives it.
- status is a sum: approved->meaning, unapproved->guidance.
- alternatives() is pure over guidance, never stored.
- pos from a closed set; qualifier/examples are Options.
- Deduplicated by (word, pos, qualifier).

Method: columns come from each page's header row (margins mirror, so no
global geometry). A non-parenthesized headword line starts a new entry;
parenthesized headwords ("(by chance) (n)") are variants of the current
entry. Split multi-word headwords ("DOWNSTREAM" / "OF (prep)") are
combined. Variants pair to senses by order; a lone variant takes the whole
entry. "Word (part of speech)" cell notes ("No other verb forms.") are
writer guidance, not lexical data, and are not captured.
"""

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "artifacts" / "ASD-STE100_ISSUE9.pdf"
OUT = ROOT / "data" / "ste100_dictionary.jsonl"

POS_TAGS = frozenset({"v", "n", "adj", "adv", "prep", "pron", "art", "conj"})
HEADER_WORDS = ("Word", "Approved", "STE", "Non-STE")

HEADWORD_RE = re.compile(
    r"^(?=[^()]*\()"  # must contain a paren group
    r"(?P<phrase>(?:\([^)]+\)|[A-Za-z][\w\-'/]*(?:\s+[\w\-'/.]+)*))"
    r"(?:\s*\((?P<paren1>(?:[a-z]+(?: [a-z]+)*|or [A-Za-z]+))\))?"
    r"(?:\s*\((?P<paren2>[a-z]+)\))?"
    r"(?P<rest>.*)$")
PHRASE_RE = re.compile(r"^[A-Za-z][\w\-'/]*(?:\s+[\w\-'/.]+)+$")
BARE_POS_RE = re.compile(r"^\(([a-z]+)\)$")
BARE_WORD_RE = re.compile(r"^[A-Za-z][\w\-'/]*$")
TRAIL_ALT_RE = re.compile(r"^([A-Z][\w\-'/]*)\s*\(([a-z]+)\)$")
ALT_REF_RE = re.compile(r"([A-Z][\w\-'/]*)\s*\(([a-z]+)\)")
FORMS_RE = re.compile(r"^[A-Za-z][\w\-',/]*(?:\s+[A-Za-z][\w\-',/]*)*$")
NOTE_RE = re.compile(r"^(No other|forms?(\.| of this)|adjective\.|verb\.|noun\.)$")
FOOTER_TEXTS = {"Issue 9", "2025-01-15",
                "ASD-STE100 Simplified Technical English",
                "Part 2 - Dictionary"}
FOOTER_RE = re.compile(r"^Page 2-1-[A-Z]\d+$")


def is_approved(record):
    word = record["word"]
    return word == word.upper() and word != word.lower()


def alternatives(record):
    status = record["status"]
    assert status["kind"] == "unapproved", "alternatives() of approved word"
    return [(m.group(1), m.group(2))
            for m in ALT_REF_RE.finditer(status["guidance"])
            if m.group(2) in POS_TAGS]


def column_starts(page):
    found = {}
    for w in page.get_text("words"):
        if w[1] < 95 and w[4] in HEADER_WORDS:
            found.setdefault(w[4], w[0])
    if set(found) != set(HEADER_WORDS):
        raise ValueError(f"header row missing: {sorted(found)}")
    return tuple(found[k] for k in HEADER_WORDS)


def body_column(x0, starts):
    if x0 >= starts[3]:
        return "nonste"
    if x0 >= starts[2]:
        return "ste"
    return "meaning"


def page_lines(page):
    data = page.get_text("dict")
    for block in data["blocks"]:
        if block.get("type", 0) != 0:
            continue
        for line in block["lines"]:
            x0, y0 = line["bbox"][0], line["bbox"][1]
            # header at y<80; first entry at y~93; keep the entry
            if y0 < 85 or y0 > 710:
                continue
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text and text not in FOOTER_TEXTS \
                    and not FOOTER_RE.match(text):
                yield x0, y0, text


def make_rows(lines):
    rows = []
    for x0, y0, text in sorted(lines, key=lambda l: l[1]):
        if rows and y0 - rows[-1][1] <= 2.5:
            rows[-1][1] = y0
            rows[-1][2].append((x0, text))
        else:
            rows.append([y0, y0, [(x0, text)]])
    return [(r[0], sorted(r[2])) for r in rows]


def parse_variant(text):
    """Parse a headword line -> (phrase, qual, pos, trail, extra).
    trail is a trailing "WORD (pos)" alternative; extra is prose meaning
    text merged onto the same line (goes to meaning)."""
    m = HEADWORD_RE.match(text)
    if not m:
        raise ValueError(f"bad headword: {text!r}")
    phrase = m.group("phrase")
    if phrase.startswith("(") and phrase.endswith(")"):
        phrase = phrase[1:-1]
    pos, qual = None, None
    p1, p2 = m.group("paren1"), m.group("paren2")
    alt_form = None
    if p1 and p1.startswith("or "):
        # alternative spelling: "MATT (or MATTE)" -> form "MATTE"
        alt_form = p1[3:].strip()
        p1 = None
    if p2:
        qual, pos = p1, p2
    elif p1:
        # single paren: pos if it's a known tag, else a qualifier
        # (pos comes on the next line)
        if p1 in POS_TAGS:
            pos = p1
        else:
            qual = p1
    else:
        # no paren1/paren2, but alt_form may exist
        if not alt_form:
            raise ValueError(f"bad headword (no paren): {text!r}")
    if pos is not None and pos not in POS_TAGS:
        raise ValueError(f"bad pos {pos!r} in {text!r}")
    trail, extra = None, None
    rest = m.group("rest").strip(" ,")
    if rest:
        tm = TRAIL_ALT_RE.match(rest)
        if tm and tm.group(2) in POS_TAGS:
            trail = (tm.group(1), tm.group(2))
        else:
            extra = rest
    return phrase, qual, pos, trail, extra, alt_form


def split_forms(text):
    # split on commas; keep multi-word phrases intact ("CAME ON")
    return [t.strip() for t in text.strip(", ").split(",") if t.strip()]


def new_entry(pageno, starts):
    return {"pageno": pageno, "starts": starts, "variants": [],
            "pending": None, "forms": [], "paren": None, "bodies": []}


def main():
    doc = pymupdf.open(PDF)
    word_pages = [i for i, p in enumerate(doc)
                  if re.search(r"Page 2-1-[A-Z]\d+", p.get_text())]
    if not word_pages:
        print("no dictionary pages", file=sys.stderr)
        return 1

    records, warnings, errors = [], [], []
    cur = None

    def warn(msg):
        warnings.append(msg)

    def emit(entry):
        if entry["pending"]:
            errors.append(f"dangling phrase {entry['pending']!r} "
                          f"p{entry['pageno']}")
            return
        if entry["paren"]:
            errors.append(f"unclosed paren {entry['paren']!r} "
                          f"p{entry['pageno']}")
            return
        variants = entry["variants"]
        if not variants:
            errors.append(f"entry without headword p{entry['pageno']}")
            return
        poses = [p for (_, _, p, _, _, _) in variants if p]
        if not poses:
            errors.append(f"entry without pos p{entry['pageno']}: "
                          f"{variants[0][0]!r}")
            return
        first_pos = poses[0]
        variants = [(ph, q, p or first_pos, tr, ex, af)
                    for (ph, q, p, tr, ex, af) in variants]
        bodies = entry["bodies"]
        starts = entry["starts"]
        if len(variants) == 1:
            senses = [bodies]
        else:
            senses, cur_sense = [], []
            first = True
            for row in bodies:
                # a new sense starts at a meaning-cell "WORD (pos)" line
                is_starter = any(
                    HEADWORD_RE.match(t) and x < starts[2]
                    for x, t in row if 150 <= x)
                if is_starter and not first:
                    senses.append(cur_sense)
                    cur_sense = []
                first = False
                cur_sense.append(row)
            senses.append(cur_sense)
            if len(senses) != len(variants):
                warn(f"sense/variant mismatch p{entry['pageno']}: "
                     f"{[v[0] for v in variants]} -> {len(senses)} senses")
        for i, (phrase, qual, pos, trail, _ex, alt_form) in enumerate(variants):
            sense = senses[min(i, len(senses) - 1)] \
                if len(variants) > 1 else senses[0]
            meaning = " ".join(t for row in sense for x, t in row
                               if body_column(x, starts) == "meaning")
            ste = " ".join(t for row in sense for x, t in row
                           if body_column(x, starts) == "ste") or None
            nonste = " ".join(t for row in sense for x, t in row
                              if body_column(x, starts) == "nonste") or None
            if trail:
                alt = f"{trail[0]} ({trail[1]})"
                meaning = f"{alt} {meaning}".strip()
            if is_approved({"word": phrase}):
                status = {"kind": "approved", "meaning": meaning.strip()}
            else:
                status = {"kind": "unapproved", "guidance": meaning.strip()}
            forms = list(entry["forms"])
            if alt_form:
                forms.append(alt_form)
            records.append({"word": phrase, "pos": pos, "qualifier": qual,
                            "forms": forms, "status": status,
                            "ste_example": ste, "nonste_example": nonste})

    for pageno in word_pages:
        page = doc[pageno]
        starts = column_starts(page)
        rows = make_rows(list(page_lines(page)))
        skip = set()  # row indices consumed by split headwords
        for i, (y, parts) in enumerate(rows):
            if i in skip:
                continue
            x0, text = parts[0]
            hw = None
            # split multi-word headword: bare word + short word (pos)
            # e.g. "DOWNSTREAM" / "OF (prep)" -> "DOWNSTREAM OF (prep)"
            split_extra = None
            if x0 < 150 and BARE_WORD_RE.match(text) and text.isupper() \
                    and i + 1 < len(rows):
                ny, nparts = rows[i + 1]
                nx0, ntext = nparts[0]
                m2 = HEADWORD_RE.match(ntext)
                if nx0 < 150 and m2 and (m2.group("paren1") or
                                        m2.group("paren2")):
                    ph2 = m2.group("phrase")
                    if not ph2.startswith("(") and len(ph2) <= 3 \
                            and ph2.isupper():
                        # combine and parse as single headword
                        try:
                            pv = parse_variant(f"{text} {ntext}")
                            hw = "full-split"
                            skip.add(i + 1)
                            # use combined text for variant
                            text = f"{text} {ntext}"
                            # capture meaning parts from skipped row
                            split_extra = [(x, t) for x, t in nparts[1:]
                                           if x >= 150]
                        except ValueError:
                            pass
            if x0 < 150 and hw is None:
                if BARE_POS_RE.match(text):
                    pass  # bare "(pos)"; handled in word-cell logic below
                elif (m := HEADWORD_RE.match(text)) and \
                        (m.group("paren1") or m.group("paren2")):
                    hw = "full"
                elif PHRASE_RE.match(text) and x0 <= starts[0] + 10 \
                        and i + 1 < len(rows):
                    # phrase headword only if next line supplies its pos
                    ny, nparts = rows[i + 1]
                    nx0, ntext = nparts[0]
                    if nx0 < 150 and BARE_POS_RE.match(ntext):
                        hw = "phrase"
                elif BARE_WORD_RE.match(text) and i + 1 < len(rows):
                    # bare headword only if next line supplies its pos
                    # (bare "(pos)" or parenthesized variant), not a
                    # different headword (which means this is a form)
                    ny, nparts = rows[i + 1]
                    nx0, ntext = nparts[0]
                    if nx0 < 150 and (
                            BARE_POS_RE.match(ntext) or
                            (ntext.startswith("(") and
                             HEADWORD_RE.match(ntext))):
                        hw = "bare"
            if hw:
                # Parenthesized headwords ("(by chance) (n)") are variants
                # of the current entry. All other headwords start a new
                # entry. Horizontal rules are a hint, not the signal.
                is_variant = hw == "full" and text.startswith("(")
                if not is_variant:
                    if cur:
                        emit(cur)
                    cur = new_entry(pageno, starts)
                # else: variant of cur; keep accumulating
                if hw == "full" or hw == "full-split":
                    pv = parse_variant(text)
                    cur["variants"].append(pv)
                    if pv[4]:
                        cur["bodies"].append([(200.0, pv[4])])
                elif hw == "phrase":
                    if cur["pending"]:
                        errors.append(f"dangling phrase {cur['pending']!r}")
                    cur["pending"] = text
                else:  # bare
                    cur["variants"].append((text, None, None, None, None, None))
                rest = [(x, t) for x, t in parts[1:] if x >= 150]
                if rest:
                    cur["bodies"].append(rest)
                # meaning parts from split headword's second row
                if split_extra:
                    cur["bodies"].append(split_extra)
                # word-cell parts beyond the headword on this row: none
                # expected; anything there is logged below via word cont
                for x1, t1 in parts[1:]:
                    if x1 < 150:
                        warn(f"extra word-cell part p{pageno}: {t1!r}")
            else:
                if cur is None:
                    continue
                wparts = [(x, t) for x, t in parts if x < 150]
                bparts = [(x, t) for x, t in parts if x >= 150]
                for x1, t1 in wparts:
                    if cur["paren"] is not None:
                        cur["paren"] += " " + t1
                        if t1.rstrip().endswith(")"):
                            inner = cur["paren"].strip()[1:]
                            if inner.endswith(")"):
                                inner = inner[:-1]
                            for tok in inner.split(","):
                                tok = tok.strip()
                                if tok and tok.lower() != "also":
                                    cur["forms"].append(tok)
                            cur["paren"] = None
                    elif BARE_POS_RE.match(t1):
                        pos = BARE_POS_RE.match(t1).group(1)
                        if pos not in POS_TAGS:
                            errors.append(f"bad pos {pos!r} p{pageno}")
                        elif cur["pending"]:
                            cur["variants"].append(
                                (cur["pending"], None, pos, None, None, None))
                            cur["pending"] = None
                        elif cur["variants"] and \
                                cur["variants"][-1][2] is None:
                            # pos for a qualifier-only headword
                            # ("provided (that)" / "(conj)")
                            ph, q, _, tr, ex, af = cur["variants"][-1]
                            cur["variants"][-1] = (ph, q, pos, tr, ex, af)
                        # else: stray; ignore
                    elif t1.startswith("("):
                        cur["paren"] = t1
                        if t1.rstrip().endswith(")"):
                            inner = t1.strip()[1:-1]
                            for tok in inner.split(","):
                                tok = tok.strip()
                                if tok and tok.lower() != "also":
                                    cur["forms"].append(tok)
                            cur["paren"] = None
                    elif NOTE_RE.match(t1):
                        pass  # writer guidance, not lexical data
                    elif FORMS_RE.match(t1):
                        cur["forms"].extend(split_forms(t1))
                    else:
                        warnings.append(f"unhandled word cell p{pageno}: "
                                        f"{t1!r}")
                if bparts:
                    cur["bodies"].append(bparts)
    if cur:
        emit(cur)

    # deduplicate by (word, pos, qualifier); keep first
    seen = set()
    uniq = []
    for r in records:
        k = (r["word"], r["pos"], r["qualifier"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    records = uniq

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    dup = Counter((r["word"], r["pos"]) for r in records)
    dups = [k for k, v in dup.items() if v > 1]
    n_appr = sum(1 for r in records if is_approved(r))
    print(f"{len(records)} records, {n_appr} approved, "
          f"{len(warnings)} warnings, {len(errors)} errors",
          file=sys.stderr)
    for w in warnings[:15]:
        print(f"WARN {w}", file=sys.stderr)
    for e in errors[:15]:
        print(f"ERROR {e}", file=sys.stderr)
    if dups:
        print(f"DUP KEYS ({len(dups)}): {dups[:12]}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
