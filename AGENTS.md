# AGENTS.md

Agent instructions for ste-tax. Human-facing docs live in README.md and
docs/. This file is for agents doing work in this repo.

## Workflow

- Work directly on `main`. No feature branches.
- Never force-push. History is append-only.
- Push small, independently auditable milestones frequently.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `data:`, `refactor:`.
- Keep prose terse. Caveman style. No commentative sentences.
- Apply ASD-STE100 principles to own writing: short sentences, one meaning
  per word.

## Build

`uv run scripts/build.py` reads `artifacts/ASD-STE100_ISSUE9.pdf` and
writes every artifact under `data/`. Parse finishes before first write;
failure leaves `data/` as it was. Exit 1 on parse error.

`uv run scripts/verify.py` checks the artifacts. Exit 1 on any failure.
Run it before each `data:` commit. Its docstring lists what it does not
check.

Scripts:
- `spec.py`: source block, schema version, atomic JSON writer.
- `extract_dictionary.py`: Part 2 to dictionary and lexicon.
- `extract_rules.py`: Part 1 rule list joined to authored paraphrases and
  parameters.
- `validate.py`: naive vocabulary check over `data/lexicon.json`.

## Artifacts

Every file: `schema_version` (1) and `source` (title, issue 9, date
2025-01-15, URL, PDF SHA-256).

- `dictionary.json`: `entries`, one per headword. Key (`word`, `pos`,
  `qualifier`), unique. `word` keeps source case; uppercase = approved.
  `status` is a sum: `approved` (meaning, help, alternatives for other
  meanings) or `unapproved` (alternatives, help, note). Alternative is a
  sum: `word` (word, pos), `technical` (word, class TN or TV), `phrase`.
- `lexicon.json`: lowercase. `approved`: id `"word (pos)"`, forms,
  derived `plural` for nouns. `unapproved`: alternatives as `ref` to an
  approved id (with `form` or `stated_pos` when the spec names a form or
  a different pos), `technical`, or `phrase`; `help` is the spec's help
  text, the only guidance for an entry with no alternative.
- `rules.json`: 53 rules: id, section, title, paraphrase, check kind,
  parameters.
- `manifest.json`: path, SHA-256, bytes of each artifact.

## Parser notes

- Approval derived from case only.
- Columns from each page header row. Bold word-column text = lexical
  data; plain word-column text = writer guidance, dropped.
- Column-2 line indented 29 pt or more = help text. Measured: wrapped
  numbered senses sit at 12 to 27, help at 30 to 43.
- Word column of whole dictionary = one token stream, one compiled
  pattern. Every headword starts an entry. Body = rows to next headword.
- Line-end hyphen inside a word is soft: `COUNTERCLOCK-` / `WISE (adv)`
  = `COUNTERCLOCKWISE`. Old parser split these into false entries
  (`WISE`, `TORY`, `NETIC`, `ABLE`).
- `chance` / `(by chance) (n)` = one entry, qualifier `by chance`, same
  as `few (a few) (adj)`.
- Spec prints forms without commas (`OCCUR`, `PROTRUDE`, `CONTACT`). A
  tagless word run under a black entry rule = headword with no pos
  (`FOR EXAMPLE`, `such as`); without the rule = more forms.
- `re- (prefix)`: the one affix entry; pos `prefix`.
- Page top cutoff y=85. First entry at y~93; header at y<80.
- Counts (2026-10-07): 2198 entries. Approved 879 by key, 806 distinct
  words; spec states 875. Not approved 1319 by key, 1251 distinct
  words; spec states 1274. Bases tried, none gives both: by key (879,
  1319), distinct word (806, 1251), tagged only (878, 1318), no
  qualifier (879, 1306), single-word only (860, 1277). The 208 approved
  verbs equal the spec's own verb list exactly, so the gap is not
  missing verbs. Highlights list 11 approved words added and 1 removed
  in Issue 9; the stated counts may predate some changes. Unresolved;
  the spec intro does not state its basis.

## Design docs

`docs/design.md` holds the research design: interventions, axes,
operationalization, compliance checker plan. Update it when the design
changes. Keep it strictly necessary and sufficient.
