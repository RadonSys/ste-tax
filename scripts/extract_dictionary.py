"""Parse ASD-STE100 Issue 9 Part 2 (the dictionary) into typed entries.

Input: artifacts/ASD-STE100_ISSUE9.pdf, pages labeled "Page 2-1-*".
Output (via scripts/build.py): data/dictionary.json, data/lexicon.json.

Entry, one per headword (key: word, pos, qualifier):
  word        headword, source case kept; UPPERCASE = approved
  pos         n | v | adj | adv | prep | pron | art | conj | prefix
              (prefix: only "re-", the one affix the dictionary lists)
  qualifier   str | null; "few (a few) (adj)" -> "a few"
  forms       inflected forms from the word cell, source case
  status      {"kind": "approved", "meaning", "help", "alternatives"}
            | {"kind": "unapproved", "alternatives", "help", "note"}
  ste_example, nonste_example, page

Alternative (a sum):
  {"kind": "word", "word", "pos"}       approved word, resolves in lexicon
  {"kind": "technical", "word", "class"} TN or TV, outside the dictionary
  {"kind": "phrase", "text"}            approved words with no pos tag

Method:
- Columns come from each page's header row; margins mirror, so no global
  geometry. A word belongs to the column whose start it passes, with a
  10 pt slack for cells set left of their header.
- Bold text in the word column is lexical data (headwords, forms). Plain
  text there ("No other verb forms.") is writer guidance and is dropped.
- A column-2 line indented 29 pt or more past the column start is help
  text, set beside the help symbol; other column-2 lines are meaning or
  alternatives.
- The word column of the whole dictionary is one token stream, cut by one
  compiled pattern. A headword is words, an optional parenthesized
  qualifier, and a pos tag; a comma after the tag opens a form list; a
  parenthesized group not followed by a tag holds more forms. A line-end
  hyphen inside a word ("COUNTERCLOCK-" / "WISE (adv)") is a soft hyphen.
- Every headword starts an entry. Its body is every table row from its
  first row to the next headword's first row, across page breaks.

Cost: w words on the 286 dictionary pages (about 10^5). Reading and the
per-page sort are O(w log w); tokenizing, parsing, and body assignment
are single linear passes. Python iterates per word or token, never per
character.
"""

import bisect
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

import pymupdf

import spec

POS_TAGS = ("n", "v", "adj", "adv", "prep", "pron", "art", "conj")
# The eight parts of speech of the spec, plus the one affix entry it lists
# in the same column: "re- (prefix)", not approved.
HEAD_TAGS = (*POS_TAGS, "prefix")
HEADER = ("Word", "Approved", "STE", "Non-STE")
PAGE_LABEL = re.compile(r"Page (2-1-[A-Z]\d+)")
COLUMN_SLACK = 10.0  # pt a cell may sit left of its header word
# pt past the column-2 start that marks help text. Measured on Issue 9:
# wrapped numbered senses sit at 12 to 27, help text at 30 to 43.
HELP_INDENT = 29.0
ROW_GAP = 2.5  # pt; words closer than this in y share a table row
RULE_ABOVE, RULE_BELOW = 7.0, 2.0  # pt; a row's top rule sits in this band
BODY_TOP, BODY_BOTTOM = 85.0, 710.0  # header row above, footer below

# One alternation, each branch a literal or a single character class, so
# the scan is linear and unambiguous.
TOKEN = re.compile(
    r"(?P<pos>\((?:" + "|".join(HEAD_TAGS) + r")\))"
    r"|(?P<open>\()|(?P<close>\))|(?P<comma>,)"
    r"|(?P<word>[^\s(),]+)"
)
# An uppercase reference: tokens of [A-Z0-9'’/-] joined by single spaces,
# then an optional tag. Token chars exclude the space, so the repetition
# has one parse; the lookarounds stop a match inside a mixed-case word.
# "CAN (CANNOT) (v)": an uppercase group directly before a tag is the
# reference's own context.
_TAGS = "|".join(POS_TAGS) + "|TN|TV"
REF = re.compile(
    r"(?<![\w'’])(?P<ref>[A-Z][A-Z0-9'’/\-]*(?: [A-Z0-9][A-Z0-9'’/\-]*)*)"
    r"(?![\w'’])(?: \((?P<inner>[A-Z][A-Z ]*)\)(?= ?\((?:" + _TAGS + r")\)))?"
    r"(?: ?\((?P<tag>" + _TAGS + r")\))?"
)
TAG = re.compile(r"\((?:" + _TAGS + r")\)")
TAG_LINE = re.compile(r"\n(?=\((?:" + _TAGS + r")\))")
# A context group (one negated class inside literal parens) or a reference.
ALT_SCAN = re.compile(r"\((?!(?:" + _TAGS + r")\))(?P<ctx>[^()]*)\)|" + REF.pattern)
LOWER = re.compile(r"[a-z]")
NOTE_TRIM = " ,;:.-–…()"


# ---- domain ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Word:
    x: float
    y: float
    text: str
    bold: bool


@dataclass(frozen=True, slots=True)
class Row:
    """One visual table row; each cell is its text on this row."""

    page: str
    ruled: bool  # a black rule tops the word cell: an entry border
    head: str  # bold word-column text
    main: str  # column 2, not help
    help: str  # column 2, indented help text
    ste: str
    nonste: str


@dataclass(frozen=True, slots=True)
class Token:
    kind: Literal["pos", "open", "close", "comma", "word", "nl"]
    text: str
    row: int


@dataclass(frozen=True, slots=True)
class Head:
    word: str
    qualifier: str | None
    pos: str | None
    forms: tuple[str, ...]
    row: int


class ParseError(ValueError):
    pass


def is_approved(word: str) -> bool:
    """Approval is the headword's case, nothing else."""
    return word == word.upper() and word != word.lower()


# ---- shell: PDF to words ----------------------------------------------------


def dictionary_pages(doc: pymupdf.Document) -> Iterator[tuple[str, pymupdf.Page]]:
    for page in doc:
        if m := PAGE_LABEL.search(page.get_text()):
            yield m.group(1), page


@dataclass(frozen=True, slots=True)
class Page:
    label: str
    starts: tuple[float, ...]  # x where each HEADER column starts
    words: tuple[Word, ...]
    rules: tuple[float, ...]  # sorted y of black rules across the word column


def read_page(label: str, page: pymupdf.Page) -> Page:
    """Column starts, body words with bold flags, and entry rules.

    Words and spans come from one TextPage, so their block and line numbers
    agree; within a line both are sorted by x and merged in one walk.
    """
    tp = page.get_textpage()
    spans: dict[tuple[int, int], list[tuple[float, bool]]] = {}
    for block in page.get_text("dict", textpage=tp)["blocks"]:
        if block.get("type", 0) != 0:
            continue
        for l_no, line in enumerate(block["lines"]):
            spans[(block["number"], l_no)] = [
                (s["bbox"][2], "Bold" in s["font"]) for s in line["spans"]
            ]
    starts: dict[str, float] = {}
    lines: dict[tuple[int, int], list[tuple[float, float, float, str]]] = {}
    for x0, y0, x1, _y1, text, b_no, l_no, _w in page.get_text("words", textpage=tp):
        if y0 < 95 and text in HEADER:
            starts.setdefault(text, x0)
        if BODY_TOP <= y0 <= BODY_BOTTOM:
            lines.setdefault((b_no, l_no), []).append((x0, y0, x1, text))
    if set(starts) != set(HEADER):
        raise ParseError(f"header row missing: {sorted(starts)}")
    words = []
    for key, ws in lines.items():
        line_spans = spans[key]
        k = 0
        for x0, y0, x1, text in sorted(ws):
            mid = (x0 + x1) / 2
            while k < len(line_spans) - 1 and line_spans[k][0] < mid:
                k += 1
            words.append(Word(x0, y0, text, line_spans[k][1]))
    w_end = starts["Approved"]
    rules = sorted(
        d["rect"].y0
        for d in page.get_drawings()
        if d.get("fill") == (0.0, 0.0, 0.0)
        and d["rect"].height < 2
        and d["rect"].x0 < w_end - COLUMN_SLACK < d["rect"].x1
    )
    return Page(label, tuple(starts[h] for h in HEADER), tuple(words), tuple(rules))


# ---- core: words to rows ----------------------------------------------------


def rows_of(page: Page) -> list[Row]:
    """Cluster words into table rows by y, then split each row by column."""
    starts = page.starts
    w_end, ste_at, non_at = (s - COLUMN_SLACK for s in starts[1:])
    clusters: list[list[Word]] = []
    last_y = float("-inf")
    for w in sorted(page.words, key=lambda w: (w.y, w.x)):
        if w.y - last_y > ROW_GAP:
            clusters.append([])
        clusters[-1].append(w)
        last_y = w.y
    rows = []
    for cluster in clusters:
        cells: dict[str, list[str]] = {"head": [], "c2": [], "ste": [], "nonste": []}
        c2_x = None
        for w in sorted(cluster, key=lambda w: w.x):
            if w.x < w_end:
                if w.bold:
                    cells["head"].append(w.text)
            elif w.x < ste_at:
                c2_x = w.x if c2_x is None else c2_x
                cells["c2"].append(w.text)
            elif w.x < non_at:
                cells["ste"].append(w.text)
            else:
                cells["nonste"].append(w.text)
        c2 = " ".join(cells["c2"])
        is_help = c2_x is not None and c2_x >= starts[1] + HELP_INDENT
        top = cluster[0].y
        k = bisect.bisect_left(page.rules, top - RULE_ABOVE)
        rows.append(
            Row(
                page.label,
                k < len(page.rules) and page.rules[k] <= top + RULE_BELOW,
                " ".join(cells["head"]),
                "" if is_help else c2,
                c2 if is_help else "",
                " ".join(cells["ste"]),
                " ".join(cells["nonste"]),
            )
        )
    return rows


def join_soft_hyphens(rows: Sequence[Row]) -> list[Row]:
    """'COUNTERCLOCK-' then 'WISE (adv)' -> 'COUNTERCLOCKWISE (adv)'."""
    out = list(rows)
    for i in range(len(out) - 1):
        head, nxt = out[i].head, out[i + 1].head
        if len(head) > 1 and head.endswith("-") and head[-2].isalpha() and nxt[:1].isalpha():
            out[i] = replace(out[i], head=head[:-1] + nxt)
            out[i + 1] = replace(out[i + 1], head="")
    return out


# ---- core: word column to headwords -----------------------------------------


def tokens_of(rows: Sequence[Row]) -> list[Token]:
    out = []
    for i, row in enumerate(rows):
        for m in TOKEN.finditer(row.head):
            kind = m.lastgroup
            assert kind is not None
            out.append(Token(kind, m.group(), i))  # type: ignore[arg-type]
        out.append(Token("nl", "", i))
    return out


def parse_heads(toks: Sequence[Token], ruled: Sequence[bool]) -> list[Head]:
    """Recursive descent over the word-column stream; raises on bad input.

    One ambiguity needs geometry: a word run that ends at an empty row with
    no tag is a headword with no part of speech ("FOR EXAMPLE") when a rule
    tops its row, and otherwise more forms of the entry above, set without
    commas ("PROTRUDE (v)" / "PROTRUDES" / "PROTRUDED" / "PROTRUDED").
    """
    n = len(toks)

    def skip_nl(i: int) -> int:
        while i < n and toks[i].kind == "nl":
            i += 1
        return i

    def kind(i: int) -> str:
        return toks[i].kind if i < n else "eof"

    def paren(i: int) -> tuple[str, int]:
        """toks[i] is '('; return the inner text and the index after ')'."""
        parts: list[str] = []
        i += 1
        while kind(i) not in ("close", "eof", "open", "pos"):
            t = toks[i]
            if t.kind == "comma":
                parts.append(",")
            elif t.kind == "word":
                parts.append(" " + t.text)
            i += 1
        if kind(i) != "close":
            raise ParseError(f"unclosed paren at row {toks[i - 1].row}")
        return "".join(parts).strip(), i + 1

    def opens_head(i: int) -> bool:
        """Is toks[i] a '(...)' followed by a pos tag (a qualifier)?"""
        if kind(i) != "open":
            return False
        _, j = paren(i)
        return kind(skip_nl(j)) == "pos"

    def starts_forms(i: int) -> bool:
        """Is toks[i] a one-row word run ended by a comma (a form item)?"""
        j = i
        while kind(j) == "word" and toks[j].row == toks[i].row:
            j += 1
        return j > i and kind(j) == "comma"

    def form_list(i: int, forms: list[str]) -> int:
        while True:
            i = skip_nl(i)
            start, item = i, list[str]()
            while kind(i) == "word" and (not item or toks[i].row == toks[start].row):
                item.append(toks[i].text)
                i += 1
            if not item and kind(i) == "open":
                return i  # "IS, WAS," then "(also ARE, WERE)"
            if not item:
                raise ParseError(f"empty form at row {toks[start].row}")
            if kind(i) == "pos" or opens_head(i):
                return start  # a trailing comma; this item is the next headword
            forms.append(" ".join(item))
            if kind(i) != "comma":
                return i
            i += 1

    heads: list[Head] = []
    i = skip_nl(0)
    while i < n:
        first = toks[i].row
        run: list[Token] = []
        while kind(i) == "word" or (kind(i) == "nl" and kind(i + 1) != "nl"):
            if toks[i].kind == "word":
                run.append(toks[i])
            i += 1
        phrase = [t.text for t in run]
        if not phrase:
            raise ParseError(f"headword without words at row {first}")
        qualifier, forms = None, []
        if kind(i) == "open":
            inner, i = paren(i)
            i = skip_nl(i)
            if inner.startswith("or "):
                forms.append(inner[3:])  # "MATT (or MATTE)": a spelling variant
            else:
                qualifier = inner
        pos: str | None = None
        if kind(i) == "pos":
            pos = toks[i].text[1:-1]
            i += 1
        elif kind(i) not in ("nl", "eof") or qualifier is not None or forms:
            raise ParseError(f"no part of speech after {' '.join(phrase)!r} at row {first}")
        elif heads and not ruled[first]:
            last = heads.pop()  # forms set without commas
            by_row: dict[int, list[str]] = {}
            for t in run:
                by_row.setdefault(t.row, []).append(t.text)
            more = tuple(" ".join(ws) for ws in by_row.values())
            heads.append(replace(last, forms=last.forms + more))
            i = skip_nl(i)
            continue
        # else: a ruled row with no tag, a headword with no part of speech
        if kind(i) == "comma":
            i = form_list(i + 1, forms)
        elif starts_forms(skip_nl(i)):
            i = form_list(i, forms)  # "CONTACT (v)" then "CONTACTS," with no comma
        j = skip_nl(i)
        if kind(j) == "open" and not opens_head(j):
            inner, i = paren(j)
            forms.extend(f.strip() for f in inner.removeprefix("also ").split(",") if f.strip())
        heads.append(Head(" ".join(phrase), qualifier, pos, tuple(forms), first))
        i = skip_nl(i)
    return heads


def check_case(head: Head) -> None:
    """A headword and its forms share one case; mixed case is a misparse."""
    upper = is_approved(head.word)
    if not (upper or head.word == head.word.lower()):
        raise ParseError(f"mixed-case headword {head.word!r} at row {head.row}")
    for form in head.forms:
        if is_approved(form) != upper:
            raise ParseError(f"form {form!r} disagrees in case with {head.word!r}")


# ---- core: headwords and bodies to entries ----------------------------------


def alternatives(lines: Sequence[str]) -> tuple[list[dict[str, Any]], str | None]:
    """Split column-2 lines into alternatives and the prose left over.

    A reference never spans a line; a tag alone on a line joins the line
    above. A parenthesized group that is not a tag, "(WITH A CLIP [TN] OR
    CLIPS [TN])", may wrap and is the context of the alternative before it.
    """
    text = TAG_LINE.sub(" ", "\n".join(lines))
    alts: list[dict[str, Any]] = []
    rest: list[str] = []
    for m in ALT_SCAN.finditer(text):
        if m.group("ctx") is not None:
            ctx = " ".join(m.group("ctx").split())
            if alts:
                alts[-1]["context"] = ctx
            else:
                rest.append(f"({ctx})")
            continue
        ref, tag, inner = m.group("ref"), m.group("tag"), m.group("inner")
        if tag in ("TN", "TV"):
            alts.append({"kind": "technical", "word": ref, "class": tag, "context": inner})
        elif tag:
            alts.append({"kind": "word", "word": ref, "pos": tag, "context": inner})
        else:
            alts.append({"kind": "phrase", "text": ref, "context": None})
    rest.append(ALT_SCAN.sub(" ", text))
    note = " ".join(" ".join(rest).split()).strip(NOTE_TRIM)
    return alts, (note or None)


def is_alt_line(line: str) -> bool:
    """A column-2 line of references only: no lowercase outside tags."""
    return not LOWER.search(TAG.sub("", line))


def entry_of(head: Head, body: Sequence[Row]) -> dict[str, Any]:
    main = [r.main for r in body if r.main]
    help_text = " ".join(r.help for r in body if r.help) or None
    status: dict[str, Any]
    if is_approved(head.word):
        # Before the first help line: the meaning. After it, reference-only
        # lines are alternatives for meanings that are not approved.
        seen_help, meaning, alt_lines = False, list[str](), list[str]()
        for r in body:
            seen_help = seen_help or bool(r.help)
            if r.main:
                (alt_lines if seen_help and is_alt_line(r.main) else meaning).append(r.main)
        alts, _ = alternatives(alt_lines)
        status = {
            "kind": "approved",
            "meaning": " ".join(meaning),
            "help": help_text,
            "alternatives": alts,
        }
    else:
        alts, note = alternatives(main)
        status = {"kind": "unapproved", "alternatives": alts, "help": help_text, "note": note}
    return {
        "word": head.word,
        "pos": head.pos,
        "qualifier": head.qualifier,
        "forms": list(head.forms),
        "status": status,
        "ste_example": " ".join(r.ste for r in body if r.ste) or None,
        "nonste_example": " ".join(r.nonste for r in body if r.nonste) or None,
        "page": body[0].page,
    }


def entries_of(rows: Sequence[Row]) -> list[dict[str, Any]]:
    heads = parse_heads(tokens_of(rows), [r.ruled for r in rows])
    for h in heads:
        check_case(h)
    ends = [h.row for h in heads[1:]] + [len(rows)]
    entries = [entry_of(h, rows[h.row : end]) for h, end in zip(heads, ends, strict=True)]
    seen: set[tuple[str, str, str | None]] = set()
    for e in entries:
        key = (e["word"], e["pos"], e["qualifier"])
        if key in seen:
            raise ParseError(f"duplicate key {key}")
        seen.add(key)
    return entries


# ---- lexicon ----------------------------------------------------------------


def plural(noun: str) -> str:
    """Regular English plural of the last word. The spec permits the plural
    of countable nouns but lists only the singular, so this is derived."""
    head, _, last = noun.rpartition(" ")
    if last.endswith(("s", "x", "z", "ch", "sh")):
        last += "es"
    elif last.endswith("y") and last[-2:-1] not in ("a", "e", "i", "o", "u"):
        last = last[:-1] + "ies"
    else:
        last += "s"
    return f"{head} {last}" if head else last


def lexicon_id(word: str, pos: str | None) -> str:
    """'aft of (prep)'; an untagged headword is its bare word."""
    return f"{word.lower()} ({pos})" if pos else word.lower()


@dataclass(frozen=True, slots=True)
class Index:
    """Lookups that resolve an alternative to an approved entry id."""

    by_key: dict[tuple[str, str | None], str]  # (word, pos) -> id
    by_form: dict[tuple[str, str | None], str]  # (form, pos) -> id
    by_word: dict[str, str]  # word -> first id, any pos
    forms: frozenset[str]  # every approved word and form

    @classmethod
    def of(cls, approved: Sequence[dict[str, Any]]) -> "Index":
        by_key: dict[tuple[str, str | None], str] = {}
        by_form: dict[tuple[str, str | None], str] = {}
        by_word: dict[str, str] = {}
        forms: set[str] = set()
        for a in approved:
            by_key[(a["word"], a["pos"])] = a["id"]
            by_word.setdefault(a["word"], a["id"])
            forms.update(a["forms"])
            for f in a["forms"][1:]:
                by_form.setdefault((f, a["pos"]), a["id"])
        return cls(by_key, by_form, by_word, frozenset(forms))

    def resolve(self, alt: dict[str, Any]) -> dict[str, str]:
        """Total over the alternative sum. A tagged word resolves, in order:
        as a headword; as a form of an entry with that pos ("FASTER (adj)");
        as a past participle used as an adjective, which rule 3.3 permits
        ("WORN (adj)" from WEAR (v)); as a phrase of approved words ("VERY
        HIGH (adj)"); as the same word under another pos, the spec's tag
        kept in `stated_pos` ("SAME (adv)"). Otherwise `unresolved`."""
        match alt["kind"]:
            case "technical":
                return {"technical": alt["word"].lower(), "class": alt["class"].lower()}
            case "phrase":
                return {"phrase": alt["text"].lower()}
            case "word":
                w, pos = alt["word"].lower(), alt["pos"]
                if ref := self.by_key.get((w, pos)):
                    return {"ref": ref}
                if ref := self.by_form.get((w, pos)) or (
                    pos == "adj" and self.by_form.get((w, "v"))
                ):
                    return {"ref": ref, "form": w}
                if " " in w and all(t in self.forms for t in w.split()):
                    return {"phrase": w}
                if ref := self.by_word.get(w):
                    return {"ref": ref, "stated_pos": pos}
                return {"unresolved": w, "stated_pos": pos}
            case other:
                raise ValueError(f"unknown alternative kind {other!r}")


def lexicon_of(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Approved words with every form, lowercased; unapproved words with
    their alternatives as ids into the approved list, and the spec's help
    text, the only guidance where an entry lists no alternative."""
    approved = [
        {
            "id": lexicon_id(e["word"], e["pos"]),
            "word": e["word"].lower(),
            "pos": e["pos"],
            "forms": list(dict.fromkeys([e["word"].lower(), *(f.lower() for f in e["forms"])])),
            "plural": plural(e["word"].lower()) if e["pos"] == "n" else None,
        }
        for e in entries
        if e["status"]["kind"] == "approved"
    ]
    index = Index.of(approved)
    unapproved = [
        {
            "word": e["word"].lower(),
            "pos": e["pos"],
            "qualifier": e["qualifier"],
            "forms": [f.lower() for f in e["forms"]],
            "alternatives": [index.resolve(a) for a in e["status"]["alternatives"]],
            "note": e["status"]["note"],
            "help": e["status"]["help"],
        }
        for e in entries
        if e["status"]["kind"] == "unapproved"
    ]
    return {"approved": approved, "unapproved": unapproved}


# ---- entry point --------------------------------------------------------------


def extract(pdf: pymupdf.Document) -> list[dict[str, Any]]:
    rows: list[Row] = []
    for label, page in dictionary_pages(pdf):
        rows.extend(rows_of(read_page(label, page)))
    if not rows:
        raise ParseError("no dictionary pages")
    return entries_of(join_soft_hyphens(rows))


def main() -> int:
    try:
        entries = extract(pymupdf.open(spec.PDF))
    except ParseError as err:
        print(f"ERROR {err}", file=sys.stderr)
        return 1
    n_appr = sum(e["status"]["kind"] == "approved" for e in entries)
    print(f"{len(entries)} entries, {n_appr} approved", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
