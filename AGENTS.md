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

## Parser

`scripts/extract_dictionary.py` extracts the dictionary from
`artifacts/ASD-STE100_ISSUE9.pdf` (pages with "Page 2-1-" markers).

Run: `uv run scripts/extract_dictionary.py`. Writes
`data/ste100_dictionary.jsonl` atomically. Exits nonzero on parse errors;
existing output is not replaced on failure.

Output schema (one JSON object per line):
- `term`: headword, source case preserved. Uppercase = approved.
- `pos`: part of speech. Closed set: n, v, adj, adv, prep, conj, pron,
  art, num.
- `qualifier`: optional parenthesized qualifier (e.g. "from", "that").
- `forms`: inflected/related forms from the word cell.
- `senses`: list of {meaning, approved_alternatives, ste_example,
  nonste_example}.
- `approved`: derived from term case. Do not store as separate field in
  new code; it is in the current output for convenience.

Key: (term, pos, qualifier). Duplicates are merged.

## Parser notes

- Approval derived from case only. No separate approved boolean in logic.
- Parenthesized headwords ("(by chance) (n)") are variants, never new
  entries.
- Non-parenthesized headwords always start new entries. Horizontal rules
  are hints, not the segmentation signal.
- Headword line may carry merged meaning text ("ADJUSTABLE (adj) That you
  can adjust"); parser splits it.
- Qualifiers may be multi-word ("in case of", "a few") or split across
  lines.
- Page top cutoff is y=85. The first entry sits at y~93; the header at
  y<80. A cutoff of 95 silently dropped the first entry on every page.
- Counts (2026-10-07): 877 approved, 2194 total. Spec intro states 875
  approved + 1274 non-approved = 2149. The 2-approved / 45-total overage
  is unresolved; likely counting-methodology differences, not missing
  entries. Verified against independent extraction: only 18 headwords
  differ, mostly reference parsing artifacts.

## Design docs

`docs/design.md` holds the research design: interventions, axes,
operationalization, compliance checker plan. Update it when the design
changes. Keep it strictly necessary and sufficient.
