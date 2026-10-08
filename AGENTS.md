# AGENTS.md

Agent instructions for ste-tax. Human-facing docs live in README.md and
docs/. This file is for agents doing work in this repo.

## Workflow

- Work directly on `main`. No feature branches.
- Never force-push. History is append-only.
- Push small, independently auditable milestones frequently.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `data:`, `refactor:`,
  `chore:` (submodule bumps).
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

## Scripts and entry points

Run from the repo root. Dev box: through uv. ROCm node: `python3`, no
uv.

| Path | Run | Does |
| --- | --- | --- |
| `scripts/build.py` | `uv run scripts/build.py` | PDF to every artifact under `data/` |
| `scripts/verify.py` | `uv run scripts/verify.py` | checks `data/`; exit 1 on a failure |
| `scripts/spec.py` | imported | source block, schema version, atomic JSON writer |
| `scripts/extract_dictionary.py` | imported by build | Part 2 to dictionary and lexicon |
| `scripts/extract_rules.py` | imported by build | Part 1 rule list joined to authored paraphrases and parameters |
| `scripts/validate.py` | `uv run scripts/validate.py -f FILE` | naive vocabulary check; the harness imports it |
| `scripts/checker_validation.py` | `uv run scripts/checker_validation.py --skill PATH/asd-ste100` | checker validation; detail file key `h` feeds `eval/gate_h.json` |
| `eval/` | `python -m eval run\|summarize\|rescore\|tasks\|preflight` | the harness; eval/README.md |
| `eval/tasks/build.py` | `python3 eval/tasks/build.py --gsm8k F --nq-open F --math500 F` | task files from pinned upstream files; docs/tasks.md |
| `eval/tasks/validate.py` | `python3 eval/tasks/validate.py` | task schema and id uniqueness |
| `eval/tasks/power.py` | `python3 eval/tasks/power.py [--sd-task S --rho R]` | sample size for the cost contrast |
| `tests/` | `uv run pytest` | harness tests |

Rules:

- `python -m eval` runs without uv inside AMD's ROCm image. The shell,
  core, loader, compliance, and mock backend import the standard
  library only; heavy imports (torch, transformers, vllm) stay inside
  their backend adapter. `tests/test_cli.py` guards the imports.
- On this machine, run uv as
  `UV_PROJECT_ENVIRONMENT=<repo>/.venv uv run ...` so no new
  environment is built. The checker binding unsets
  `UV_PROJECT_ENVIRONMENT`, or uv installs the skill into this venv.
- Never install torch, transformers, accelerate, or vllm on the dev box.

## Artifact release

The asd-ste100 checker reads `data/` from a tagged release through
jsDelivr (`https://cdn.jsdelivr.net/gh/RadonSys/ste-tax@vX.Y.Z/`).
After a `data:` change that a checker must see:

1. `uv run scripts/verify.py`; commit; push `main`.
2. `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. `gh release create vX.Y.Z --title vX.Y.Z --notes "<what changed in data/>"`.
4. CDN check: fetch `data/manifest.json` from the CDN URL, then each
   artifact it lists; each SHA-256 and byte count must equal the
   manifest, and the manifest must equal the local `data/manifest.json`.
5. A wrong file on the CDN: purge it with
   `curl https://purge.jsdelivr.net/gh/RadonSys/ste-tax@vX.Y.Z/<path>`,
   then repeat step 4. Do not move a tag; cut a new one.
6. Bump the pin in the SKILLs repository (`asd-ste100` `VERSION`), then
   the `.github/skills` submodule here; rerun
   `scripts/checker_validation.py` and update `eval/gate_h.json` when the
   checker changed.

Current release: v0.1.2 (CDN check passed 2026-10-08).

## Friction ledgers

Each delegated task keeps one ledger, `docs/friction/<task>.md`. One
row per pain point with a skill, a script, or the environment:

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |

Cost = extra tool calls. Class: `text gap`, `contract gap`, `script
bug`, `design question`. Fix location names the file, and the commit
when fixed. Small decidable SKILLs fixes go on a SKILLs branch; the
ledger names it.

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

`docs/design.md` holds the research design: prior work and gap,
interventions, axes, compliance checker. Update it when the design
changes. Keep it strictly necessary and sufficient. One topic, one
file: hardware facts in `docs/dcs-amd-hardware.md`, node procedure in
`docs/runbook.md`, protocol in `docs/experiment-plan.md`, tasks in
`docs/tasks.md`, harness reference in `eval/README.md`.
