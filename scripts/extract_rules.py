"""Read the rule list of ASD-STE100 Issue 9 Part 1 and join it to an
authored table of paraphrases and checker parameters.

Output (via scripts/build.py): data/rules.json.

The PDF gives each rule's identifier, section, and heading, read from the
"Summary of the rules" page that opens each section. This file gives the
rest, in our words: a one-sentence paraphrase, how a checker can test the
rule, and the parameters it needs. The build fails when the two rule sets
differ, so a rule cannot be added, dropped, or renumbered silently.

Rule:
  id          "5.1"
  section     {"number": 5, "title": "Procedural writing"}
  title       the heading above the rule on the summary page
  paraphrase  one sentence, not a quotation
  check       lexicon | count | pattern | heuristic | judgment
              (lexicon, count, pattern: decidable from text and the
              lexicon; heuristic: a signal with false positives; judgment:
              needs a reader)
  parameters  object; empty when nothing is decidable

Cost: one pass over the lines of 9 summary pages.
"""

import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pymupdf

import spec

SUMMARY = "Summary of the rules"
RULE_LINE = re.compile(r"Rule (\d+)\.(\d+)")
SECTION_LINE = re.compile(r"Section (\d+)\s*[–-]\s*(.+)")
PART1_LABEL = re.compile(r"Page 1-\d+-\d+")

ING_APPROVED = (
    "lighting (n)",
    "opening (n)",
    "routing (n)",
    "servicing (n)",
    "mating (adj)",
    "missing (adj)",
    "remaining (adj)",
    "something (pron)",
    "during (prep)",
)
TN_CATEGORIES = (
    "Official parts information",
    "Vehicles or machines, and locations on them",
    "Tools and support equipment, their parts, and locations on them",
    "Materials, consumables, and unwanted material",
    "Facilities, infrastructure, and logistic procedures",
    "Systems, components and circuits, their functions, configurations, and parts",
    "Mathematical, scientific, engineering terms, and formulas",
    "Navigation and geographic terms",
    "Numbers, units of measurement and time (and their symbols)",
    "Quoted text",
    "Professional roles, individuals, groups, organizations, and geopolitical entities",
    "Parts of the body",
    "Common personal effects, food, and beverages",
    "Medical terms",
    "Official documents, parts of documentation, standards, and guidelines",
    "Environmental and operational conditions",
    "Colors",
    "Damage terms",
    "Computer science, information and communication technology",
    "Civil and military operations",
    "Law and regulations",
    "Animals, plants, and other life forms",
)
TV_CATEGORIES = (
    "Manufacturing processes",
    "Computer processes and applications",
    "Instructions and information for applicable subject fields",
    "Law and regulations",
)

# id -> (paraphrase, check, parameters). Paraphrases are ours.
AUTHORED: dict[str, tuple[str, str, dict[str, Any]]] = {
    "1.1": (
        "Write only with dictionary-approved words, technical nouns, and technical verbs.",
        "lexicon",
        {"vocabulary": ["approved", "technical_noun", "technical_verb"]},
    ),
    "1.2": (
        "Give an approved word only the part of speech the dictionary assigns it.",
        "heuristic",
        {},
    ),
    "1.3": ("Give an approved word only its listed meaning.", "judgment", {}),
    "1.4": (
        "Use only the verb and adjective forms that the dictionary lists.",
        "lexicon",
        {"forms_source": "dictionary", "noun_plural_permitted": True},
    ),
    "1.5": (
        "A noun that fits one of the listed technical-noun categories may be used.",
        "judgment",
        {"technical_noun_categories": list(TN_CATEGORIES)},
    ),
    "1.6": (
        "An unapproved word is acceptable only as a technical noun or inside one.",
        "lexicon",
        {"exemption": "technical_noun"},
    ),
    "1.7": ("Never turn a technical noun into a verb.", "judgment", {}),
    "1.8": (
        "Take technical nouns from those your organization or field already accepts.",
        "judgment",
        {},
    ),
    "1.9": ("Pick technical nouns that are brief and plain.", "judgment", {}),
    "1.10": (
        "Keep regional words, slang, and jargon out of technical nouns.",
        "judgment",
        {},
    ),
    "1.11": ("Name one item with one technical noun throughout.", "judgment", {}),
    "1.12": (
        "A verb that fits one of the listed technical-verb categories may be used.",
        "judgment",
        {"technical_verb_categories": list(TV_CATEGORIES)},
    ),
    "1.13": ("Never turn a technical verb into a noun.", "judgment", {}),
    "1.14": (
        "Spell the American way unless a governing directive says otherwise.",
        "judgment",
        {"spelling": "American English"},
    ),
    "2.1": (
        "Keep each multi-word noun to three words or fewer.",
        "heuristic",
        {"max_words_in_multi_word_noun": 3},
    ),
    "2.2": (
        "Write a technical noun longer than three words in full first, then shorten or hyphenate it.",
        "judgment",
        {"max_words_in_multi_word_noun": 3},
    ),
    "3.1": ("Use a verb only in the forms that its dictionary entry gives.", "lexicon", {}),
    "3.2": (
        "Limit verbs to the infinitive, imperative, simple present, simple past, simple future, and the past participle used as an adjective.",
        "heuristic",
        {
            "permitted_verb_forms": [
                "infinitive",
                "imperative",
                "simple_present",
                "simple_past",
                "simple_future",
                "past_participle_as_adjective",
            ]
        },
    ),
    "3.3": ("Use a past participle only as an adjective.", "heuristic", {}),
    "3.4": (
        "Do not stack auxiliary verbs into compound tenses.",
        "heuristic",
        {},
    ),
    "3.5": (
        "Allow an -ing word only as a technical noun, a modifier inside one, or one of the few approved -ing words.",
        "pattern",
        {
            "ing_suffix": "ing",
            "ing_approved": list(ING_APPROVED),
            "ing_exemptions": ["technical_noun", "technical_noun_modifier"],
        },
    ),
    "3.6": (
        "Write in the active voice; descriptive text may use the passive only when the agent is unknown.",
        "heuristic",
        {"passive": {"procedure": "forbidden", "description": "agent_unknown_only"}},
    ),
    "3.7": (
        "Show an action with an approved verb, not a noun or other word class.",
        "judgment",
        {},
    ),
    "4.1": ("Keep sentences short and their structure clear.", "count", {"see": ["5.1", "6.3"]}),
    "4.2": (
        "Write every word in full: no dropped words and no contractions.",
        "pattern",
        {"contractions": "forbidden"},
    ),
    "4.3": ("Put complex content into a vertical list.", "judgment", {}),
    "4.4": (
        "Join sentences on related topics with connecting words or phrases.",
        "judgment",
        {},
    ),
    "4.5": (
        "Put an article or a demonstrative adjective before a noun where one fits.",
        "heuristic",
        {"determiners": ["the", "a", "an", "this", "these"]},
    ),
    "5.1": (
        "In procedures, keep each sentence to 20 words or fewer; notes in procedures may reach 25.",
        "count",
        {
            "mode": "procedure",
            "max_words_per_sentence": 20,
            "applies_to_safety_instructions": True,
            "notes_max_words_per_sentence": 25,
        },
    ),
    "5.2": (
        "Give one instruction per sentence unless the actions happen at the same time.",
        "heuristic",
        {"mode": "procedure", "max_instructions_per_sentence": 1},
    ),
    "5.3": (
        "Phrase instructions as commands.",
        "heuristic",
        {"mode": "procedure", "mood": "imperative"},
    ),
    "5.4": (
        "Open an instruction with any condition the reader needs first, set off from the command by a comma.",
        "judgment",
        {"mode": "procedure", "condition_separator": ","},
    ),
    "5.5": (
        "Use notes for information only, never for instructions.",
        "judgment",
        {"mode": "procedure"},
    ),
    "6.1": ("Present information step by step.", "judgment", {"mode": "description"}),
    "6.2": (
        "Structure the text with key words and key phrases.",
        "judgment",
        {"mode": "description"},
    ),
    "6.3": (
        "In descriptive text, keep each sentence to 25 words or fewer.",
        "count",
        {"mode": "description", "max_words_per_sentence": 25},
    ),
    "6.4": ("Group related information into paragraphs.", "judgment", {"mode": "description"}),
    "6.5": ("Give each paragraph a single topic.", "judgment", {"mode": "description"}),
    "6.6": (
        "Keep each paragraph to six sentences or fewer.",
        "count",
        {"mode": "description", "max_sentences_per_paragraph": 6},
    ),
    "7.1": (
        "Mark the level of risk with a signal word such as warning or caution.",
        "judgment",
        {"signal_words": ["warning", "caution"]},
    ),
    "7.2": ("Begin a safety instruction with a clear command or condition.", "judgment", {}),
    "7.3": ("Explain the risk or the possible result.", "judgment", {}),
    "8.1": (
        "Any standard English punctuation is allowed except the semicolon.",
        "pattern",
        {"forbidden_punctuation": [";"]},
    ),
    "8.2": ("Hyphenate words that belong together directly.", "judgment", {}),
    "8.3": (
        "Parentheses serve references, identifiers, step numbers, abbreviations, singular-plural pairs, explanations, and alternatives.",
        "judgment",
        {},
    ),
    "8.4": (
        "In a vertical list, a colon ends a sentence for word count, and each list item counts as its own sentence.",
        "count",
        {"colon_before_list_ends_sentence": True, "list_item_is_sentence": True},
    ),
    "8.5": (
        "Text in parentheses counts as one word of its sentence and as a sentence of its own.",
        "count",
        {"parenthetical_counts_as_words": 1, "parenthetical_is_sentence": True},
    ),
    "8.6": (
        "Count a number, number with unit, abbreviation, alphanumeric identifier, quotation, title, or proper noun as one word.",
        "count",
        {
            "count_as_one_word": [
                "number",
                "number_with_unit",
                "abbreviation",
                "alphanumeric_identifier",
                "quoted_text",
                "title_heading_placard_label",
                "proper_noun",
            ]
        },
    ),
    "8.7": ("Count a hyphenated word as one word.", "count", {"hyphenated_counts_as_words": 1}),
    "9.1": (
        "Recast the sentence when swapping words one for one is not enough.",
        "judgment",
        {},
    ),
    "9.2": ("Use every approved word correctly.", "judgment", {}),
    "9.3": ("Do not build phrasal verbs from two words.", "heuristic", {}),
    "9.4": ("Keep terminology and wording consistent.", "judgment", {}),
}


@dataclass(frozen=True, slots=True)
class Listed:
    """A rule as the summary page lists it."""

    id: str
    section: int
    section_title: str
    title: str
    statement: str


def summary_lines(doc: pymupdf.Document) -> Iterator[tuple[float, bool, str]]:
    """(font size, bold, text) of each line on each section summary, from
    the section title to the first heading of the section body."""
    for page in doc:
        text = page.get_text()
        if SUMMARY not in text or not PART1_LABEL.search(text):
            continue
        lines = (
            line
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            if 60 <= line["bbox"][1] <= 715
        )
        started = False
        for line in lines:
            spans = line["spans"]
            line_text = "".join(s["text"] for s in spans).strip()
            if not line_text:
                continue
            size = max(s["size"] for s in spans)
            bold = all("Bold" in s["font"] for s in spans if s["text"].strip())
            if SECTION_LINE.fullmatch(line_text):
                started = True
            elif started and size >= 12 and line_text != SUMMARY:
                break  # the first heading of the section body
            if started:
                yield size, bold, line_text


def listed_rules(doc: pymupdf.Document) -> list[Listed]:
    out: list[Listed] = []
    section, section_title, heading = 0, "", ""
    current: list[str] | None = None
    rule_id = ""

    def flush() -> None:
        if current is not None:
            out.append(Listed(rule_id, section, section_title, heading, " ".join(current)))

    for size, bold, text in summary_lines(doc):
        if m := SECTION_LINE.fullmatch(text):
            flush()
            current = None
            section, section_title = int(m.group(1)), m.group(2).strip()
        elif text == SUMMARY:
            continue
        elif m := RULE_LINE.fullmatch(text):
            flush()
            rule_id, current = f"{m.group(1)}.{m.group(2)}", []
        elif bold and size < 13:
            flush()
            current, heading = None, text
        elif current is not None:
            current.append(text)
    flush()
    return out


def rules_of(listed: list[Listed]) -> list[dict[str, Any]]:
    ids = [r.id for r in listed]
    if len(set(ids)) != len(ids) or set(ids) != set(AUTHORED):
        missing, extra = set(AUTHORED) - set(ids), set(ids) - set(AUTHORED)
        raise ValueError(f"rule sets differ: missing {sorted(missing)}, extra {sorted(extra)}")
    out = []
    for r in listed:
        paraphrase, check, parameters = AUTHORED[r.id]
        out.append(
            {
                "id": r.id,
                "section": {"number": r.section, "title": r.section_title},
                "title": r.title,
                "paraphrase": paraphrase,
                "check": check,
                "parameters": parameters,
            }
        )
    return out


def main() -> int:
    try:
        rules = rules_of(listed_rules(pymupdf.open(spec.PDF)))
    except ValueError as err:
        print(f"ERROR {err}", file=sys.stderr)
        return 1
    print(f"{len(rules)} rules", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
