# Checker validation

The intervention pin says: the checker defines compliance; validate it on a
labeled sample before trusting absolute rates. This document is that
validation for the asd-ste100 checker (`check`, SKILLs repository).

## Oracle

`data/dictionary.json` holds the spec's own examples. Issue 9, Part 2.

- STE example: 2,197 entries (all but `re-`). Capitals. Compliant by
  construction. Each finding on it is a false positive.
- Non-STE example: 1,358 entries. Same sentence, sentence case. For an
  unapproved headword it uses the headword. A finding on the headword is a
  true positive.

Scored Non-STE set: 1,316 unapproved headwords. Not scored: 42 examples
whose difference is meaning only (rule 1.3): approved headwords (ABOUT for
"approximately"), and unapproved entries whose word and part of speech
also have an approved entry (GET (v) approved, get (v) "become" not).
Spelling cannot separate these; the checker states it does not examine
meaning.

Oracle defects found and fixed before the run: 12 examples held text from
outside the STE column ("Blank Page" from 10 blank pages; "Curve",
"Cycle", "times." from the Non-STE column, page 2-1-C24). Fix: ste-tax
19e3fd9; `verify.py` now fails on both. `lexicon.json` did not change, so
the word data of the checker (release v0.1.1) equals the rebuilt data.
Only the example text that `lookup` shows differs, in those 12 entries.

## Method

- One `check --text:stdin --mode description` call per example, with one
  allow file. 3,855 calls, 4 workers.
- Allow list (technical nouns): each word of the STE examples that
  `lookup` does not find, in the STE examples of two or more entries, and
  no -s or -ed form of a headword. 469 terms.
- Each `not_approved` finding gets an origin from `lookup`:
  - unknown: no entry. A technical noun the allow list did not hold.
  - homograph: unapproved entries only, and either none is a noun or one
    names the word itself as a technical noun ("support (n)": SUPPORT
    (TN)). FUEL, PUMP, OIL, BOLT.
  - dictionary: other words. Checker and spec disagree.
- Headword match on Non-STE: a `not_approved` finding whose token or
  `headword` is the headword, a form, or its phrase ("finding"); a finding
  on a regular form the checker did not link ("inflected"); a signal only
  ("signal"); none ("miss").
- Probe: 300 STE examples (each 7th entry) also in sentence case. Compare
  the finding and signal sets.

Bias of the allow list. It comes from the examples it is tested on, so the
STE false-positive rate is optimistic for words in two or more examples. A
technical noun in one example stays a finding (the "unknown" rows). The
two-example rule also admits words that the dictionary lacks and that are
not nouns of a part or tool: adjectives (AMBIENT, CENTRAL, FUNCTIONAL,
STATIC, colors such as RED), number words (the checker passes those
anyway), and technical verbs (DOWNLOAD, DRILL). This document does not
decide whether each is a valid technical word. The list cannot hold a
homograph: it excludes headwords, since an allowed noun also passes as the
unapproved verb.

Reproduce:

```bash
uv run scripts/checker_validation.py --skill PATH/SKILLs/asd-ste100
uv run scripts/checker_validation.py --command "env PYTHONPATH=SRC BIN"
```

The first command binds the skill as SKILL.md does. The second runs
unreleased checker code: SRC is `asd-ste100/scripts/src` of SKILLs branch
`wt/checker`, BIN the `btm-asd-ste100` entry point of a SKILLs environment.
`--reuse` re-derives the tables from saved reports. Two runs below:

- released: SKILLs main 4404bd7.
- patched: SKILLs `wt/checker` 0ce147a (fixes in "Defects").

## Results

Cost: 0.48 to 0.52 s per call (Python start and lexicon load; `uv run`
adds little). 3,855 calls: 8.5 min on 4 workers.

### STE examples: false positives

| Kind | Released: examples with one or more | Patched |
| --- | --- | --- |
| not_approved, homograph | 700 (31.9%) | 700 (31.9%) |
| not_approved, unknown | 355 (16.2%) | 355 (16.2%) |
| not_approved, dictionary | 47 (2.1%) | 47 (2.1%) |
| ing_form | 28 (1.3%) | 28 (1.3%) |
| sentence_length | 2 (0.1%) | 0 |
| any finding (`ok: false`) | 984 (44.8%) | 984 (44.8%) |
| checker-owned (dictionary origin, or a kind other than not_approved) | 76 (3.5%) | 75 (3.4%) |
| signal: part_of_speech | 756 (34.4%) | 925 (42.1%) |
| signal: passive_candidate | 129 (5.9%) | 129 (5.9%) |
| signal: quotation | 41 (1.9%) | 41 (1.9%) |

Findings per STE example (patched): homograph 0.401, unknown 0.199,
dictionary 0.022, ing_form 0.013.

Patched adds 3 STE findings ("TURN ON THE SLEEVES" twice, "SWITCH ON THE
TEST PANEL") and removes 3 (2 sentence lengths, 1 "switch").

### Non-STE examples: headword recall

| Outcome | Released | Patched |
| --- | --- | --- |
| finding | 1,216 (92.4%) | 1,243 (94.5%) |
| inflected | 10 (0.8%) | 10 (0.8%) |
| signal only | 64 (4.9%) | 62 (4.7%) |
| miss | 26 (2.0%) | 1 (0.1%) |
| recall as a finding | 93.2% | 95.2% |
| recall with signals | 98.0% | 99.9% |

Multi-word or qualified headwords (54): released 28 found, 14 missed;
patched 50 found, 0 missed. The one patched miss: zero (v), "Zero the
meter.": number words pass before the dictionary lookup.

Signal-only hits (62): an approved word with an unapproved part of speech
of the same spelling (aid (v), back (n), break (n), check (v)), or a
regular form of one (bottoms, clicks, approved). `part_of_speech` names
the word; it does not decide.

### Confusion by part of speech (patched)

| pos | STE examples | STE with checker-owned finding | Non-STE scored | finding | inflected | signal | miss | recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v | 866 | 3.9% | 656 | 605 | 5 | 45 | 1 | 93.0% |
| adj | 523 | 2.9% | 294 | 289 | 2 | 3 | 0 | 99.0% |
| n | 452 | 3.8% | 211 | 201 | 0 | 10 | 0 | 95.3% |
| adv | 215 | 3.3% | 101 | 98 | 0 | 3 | 0 | 97.0% |
| prep | 78 | 1.3% | 32 | 32 | 0 | 0 | 0 | 100.0% |
| conj | 31 | 0.0% | 14 | 10 | 3 | 1 | 0 | 92.9% |
| pron | 27 | 3.7% | 7 | 7 | 0 | 0 | 0 | 100.0% |

Verbs lose most: 45 of 656 verb headwords are signal only, because the
same spelling is an approved noun (CHECK, BREAK, AID).

### Confusion by finding kind (patched)

Share of examples with the kind. A kind that separates the two columns
can gate; one that does not is noise.

| Kind | STE | Non-STE |
| --- | --- | --- |
| not_approved, dictionary | 2.1% | 22.8% |
| not_approved, homograph | 31.9% | 84.7% |
| not_approved, unknown | 16.2% | 18.5% |
| ing_form | 1.3% | 5.3% |
| contraction | 0.0% | 0.1% |
| sentence_length | 0.0% | 0.1% |
| signal: part_of_speech | 42.1% | 38.7% |
| signal: passive_candidate | 5.9% | 12.6% |
| signal: abbreviation | 0.0% | 0.9% |
| signal: quotation | 1.9% | 0.2% |

On the Non-STE side "homograph" is mostly the headword itself (abandon,
utilize: unapproved verbs with no noun entry). The origin is a property of
the dictionary, not of the use.

### Gate options (patched)

H: the 93 homograph tokens found in two or more STE examples. In-sample.

| Gate: findings that reject a text | STE rejected | Non-STE headword caught |
| --- | --- | --- |
| every finding (`ok`) | 984 (44.8%) | 1,253 (95.2%) |
| every finding but unknown words | 755 (34.4%) | 1,236 (93.9%) |
| every finding but unknown words and H | 123 (5.6%) | 1,179 (89.6%) |
| every finding but unknown words, H, and ing_form | 97 (4.4%) | 1,172 (89.1%) |
| form only: contraction, semicolon, length | 0 (0.0%) | 0 (0.0%) |

Released checker: same STE column but 2 form-only rejects; caught 1,226,
1,213, 1,155, 1,148, 0. H then holds 92 tokens.

### Worst STE offenders (patched, checker-owned findings)

| Entry | Findings | Text |
| --- | --- | --- |
| devise (v) | ing_form holding, not_approved support | IF THE HOLDING FIXTURE IS NOT AVAILABLE, MAKE A SUPPORT FROM THE SHIPPING CONTAINER. |
| fail (v) | failure, isolation | ... FAILURE OF THE EMERGENCY FLOTATION GEAR CAN OCCUR. ... DO THE FAULT ISOLATION PROCEDURE. |
| garner (v) | failures, failure | THE BITE FUNCTION COLLECTS THE FAILURES AND SENDS THE FAILURE MESSAGE ... |
| accelerate (v) | process | TO MAKE THE CURING PROCESS FASTER, APPLY HEAT TO THE COMPOUND. |
| ahead (adv) | alignment | THE ALIGNMENT ARROW MUST POINT FORWARD. |
| CAUSE (v) | interference | METAL OBJECTS CAN CAUSE MAGNETIC INTERFERENCE. |
| compile (v) | form | RECORD THE AILERON MOVEMENTS ON FORM B. |
| arise (v) | ing_form loading | SHOCK LOADING OF THE ENGINE CAN OCCUR ... |
| categorize (v) | ing_form testing | THE TESTING EQUIPMENT DIVIDES THE FAULTS INTO CATEGORIES. |

Most frequent: failure 10+3, interference 6, isolation 6, process 3, form
3, regulations 3. Each is a word the dictionary lists as not approved
(failure (n), isolation (n)) inside a technical name (FAULT ISOLATION
PROCEDURE, FAILURE MESSAGE). These are spec-internal: the checker is
right by the dictionary, the example is right by rule 1.5 (technical
nouns). The 28 `ing_form` items are -ing words in technical nouns
(PARKING BRAKE), which rule 3.5 permits once declared.

Most frequent homographs: fuel 68, oil 43, pump 42, switch 38, power 32,
cover 32, filter 32, bolts 31, bolt 21, wire 20, grease 20.

### Probe: capitals and sentence case

300 STE examples: reports equal in capitals and in sentence case (0
differ). Capitals do not change word findings here. One case effect was
found outside the probe: the capitals switch was decided once per text
(more upper than lower letters), so one capital sentence changed label
handling in all other sentences. Fixed: per sentence (SKILLs 2e84a65).

## Defects

| # | Defect | Evidence | Where fixed |
| --- | --- | --- | --- |
| 1 | "Blank Page" in 10 STE examples | dust, zero, KNOW, ... | ste-tax 19e3fd9 extractor; `verify.py` check |
| 2 | Non-STE words in 2 STE examples (column slack 10 pt, cell at 10.1) | curve, cycle | ste-tax 19e3fd9 |
| 3 | Capitals decided per text, not per sentence | batch of mixed texts; warning in capitals inside a manual passed unchecked | SKILLs 2e84a65, test |
| 4 | Multi-word headwords never matched | 14 misses: turn off, get to, up to, have to | SKILLs 8018093, 0ce147a, tests |
| 5 | Qualified entries keyed by the bare word | CURING PROCESS, FILTER CASE flagged; no longer missed | SKILLs 8018093, 0ce147a, tests |
| 6 | Hyphenated headwords passed as compounds | air-dry, left-hand, right-hand, hand-tight, hand-tighten | SKILLs 8018093, test |
| 7 | No sentence end after a closing quotation mark | 2 STE sentence_length | SKILLs 8018093, test |
| 8 | Part-of-speech signal ignored regular forms; `lookup` did not | bottoms, sounds, travels, clicks, approved | SKILLs 8018093, test |
| 9 | Phrase match after an article | THE REAR OF THE UNIT, A COLOR CODE | SKILLs 0ce147a, test |
| 10 | Homographs are findings | 31.9% of STE examples | open: design question |
| 11 | Phrasal verb or verb plus preposition | TURN ON THE SLEEVES | open: design question |
| 12 | Number word as verb | Zero the meter. | open: design question |
| 13 | Meaning-only entries | 42 Non-STE examples, 39 missed | not decidable by spelling (rule 1.3) |

## Verdict

Gate on, trusted:

- `not_approved` with dictionary origin: 2.1% of STE examples, 22.8% of
  Non-STE. Its STE residue is spec-internal (FAULT ISOLATION).
- `contraction`, `punctuation`, `sentence_length`, `paragraph_length`:
  0 STE false positives after the patch. They catch only form, so they
  never measure vocabulary.
- `not_approved` with homograph origin, except the spec-attested
  technical nouns (H).

Together: gate row 4, "every finding but unknown words, H, and ing_form".
4.4% STE false rejects, 89.1% headword recall (patched checker). Use it
with a per-task allow list for unknown words.

Signals, never gates:

- `not_approved` on a word not in the dictionary: it measures the allow
  list, not the text (16.2% vs 18.5%).
- `not_approved` on H tokens: the spec's own STE examples use FUEL, PUMP,
  OIL as nouns; the checker cannot tell the noun from the verb.
- `ing_form`: 1.3% vs 5.3%. Mostly technical nouns.
- `part_of_speech`: 42.1% of STE vs 38.7% of Non-STE. No information.
- `passive_candidate`: 5.9% vs 12.6%. Descriptions use the passive
  legally.

Absolute compliance rates from `ok` are not trustworthy: `ok` rejects
44.8% of the spec's own STE examples. Report compliance as the rate under
gate row 4, with the allow list per task, and state the 4.4% floor and the
89.1% recall beside it. The harness needs `lookup` for each distinct
flagged word to know its origin, and the H list (key `h` of the detail
file this script writes). Arm comparisons (A0, A1, A2) under one gate and
one allow list stay valid: the error is the same in each arm, but it is
not independent of the text, so state that assumption.

Limits. The Non-STE examples are one-word substitutions; real model output
has more than one error in a sentence, so recall here is per headword, not
per text. The probe covered capitals only for the spec's sentence shapes.
The allow list is in-sample.
