# Friction backlog

Consolidated from the five wave-1 ledgers, the asd-ste100 "Possible
problems" section, and the lead's session notes. One row per distinct
item after dedup. Built 2026-10-08.

Ledger codes: `harness#N`, `tasks#N`, `checker#N`, `watermark#N`,
`research#N`, `backlog-delegate#N` = row N of
docs/friction/<name>.md. `ste100-pp` = SKILLs
asd-ste100/SKILL.md "Possible problems". `notes` = lead's session notes.

Status: `fixed <commit>` (SKILLs main or ste-tax main hash), `open
<issue>`, or `closed: <reason>` (no fix wanted). Classes as in the
ledgers. Home: where the fix lands. `L1`..`L4` mark a law (see Laws).

| Id | Skill | Class | Statement | Ledgers | Status | Home |
| --- | --- | --- | --- | --- | --- | --- |
| B01 | asd-ste100 | design question | `check` and `lookup` read only the pinned release from a network-filled cache; no flag names a local `data/` directory | harness#1, notes | open https://github.com/BTreeMap/SKILLs/issues/2 | asd-ste100 script: `--data DIR` |
| B02 | asd-ste100 | design question | No batch mode: one process per text, 0.43 to 0.52 s each (Python start and lexicon load); 3,855 texts took 8.5 min | harness#2, checker#1, notes | open https://github.com/BTreeMap/SKILLs/issues/3 | asd-ste100 script: `check --jsonl`, lexicon loaded once |
| B03 | asd-ste100 | contract gap | Report has no schema version; the 170c269 report lacks `summary`; stable fields are not named (L2) | harness#3, notes | open https://github.com/BTreeMap/SKILLs/issues/4 | kernel helper for `schema_version`; asd-ste100 text names stable fields |
| B04 | asd-ste100 | text gap | Text did not say one `not_approved` item per distinct word | harness#4 | fixed 3b647e9 | asd-ste100 text |
| B05 | library | text gap | `compatibility` names uv and a full checkout but not the environment size (222 MB) or location (L1) | harness#5 | open https://github.com/BTreeMap/SKILLs/issues/5 | author-skill standard: `compatibility` states size and location |
| B06 | asd-ste100 | design question | No `check --mode` for short answers (math, QA) that are neither procedure nor description | harness#7 | open https://github.com/BTreeMap/SKILLs/issues/6 | asd-ste100 text |
| B07 | asd-ste100 | text gap | Text said a finding "gives the word"; the field is `token` | tasks#8 | fixed 2a9ab80 | asd-ste100 text |
| B08 | asd-ste100 | text gap | `lookup` entry shape undocumented: `status` is an object (`kind`, `meaning`, `alternatives`); `pos` is absent for a headword with no part of speech, KeyError after an 8-min run (L2) | tasks#9, checker#19 | open https://github.com/BTreeMap/SKILLs/issues/7 | asd-ste100 text, or a `schema` verb |
| B09 | asd-ste100 | design question | Technical-noun step 1 lists materials but not physical quantities (air, pressure, temperature) | tasks#10 | open https://github.com/BTreeMap/SKILLs/issues/8 | asd-ste100 text |
| B10 | asd-ste100 | script bug | Capitals switch decided per text, not per sentence; text said "all in capital letters" | checker#2, checker#3 | fixed c02725b | asd-ste100 script and text |
| B11 | library | contract gap | Every binding unsets `VIRTUAL_ENV` only; with `UV_PROJECT_ENVIRONMENT` set, `uv run --project` installs the skill into the caller's `.venv` (L1) | checker#4, backlog-delegate#6, notes | open https://github.com/BTreeMap/SKILLs/issues/9 | author-skill `references/scripts.md` binding plus every skill binding: add `-u UV_PROJECT_ENVIRONMENT` |
| B12 | asd-ste100 | text gap | Report field `next` ("not in the dictionary: ...") is not in "The report" (L2) | checker#5 | open https://github.com/BTreeMap/SKILLs/issues/10 | asd-ste100 text |
| B13 | asd-ste100 | script bug | `pos_signal` did not try stems: `check` passed "bottoms" with no signal | checker#6 | fixed 9d3db4a | asd-ste100 script |
| B14 | asd-ste100 | script bug | Multi-word and qualified headwords never matched, or keyed by the bare word | checker#7, checker#8 | fixed 9d3db4a, 10a1305 | asd-ste100 script |
| B15 | asd-ste100 | script bug | Hyphenated headwords passed as compounds before the headword lookup | checker#9 | fixed 9d3db4a | asd-ste100 script |
| B16 | asd-ste100 | script bug | No sentence end after a closing quotation mark | checker#10 | fixed 9d3db4a | asd-ste100 script |
| B17 | asd-ste100 | design question | Homographs are findings: a technical noun spelled like an unapproved verb (FUEL, PUMP, OIL) fails 31.9% of the spec's own STE examples; needs part of speech | checker#11, notes | open https://github.com/BTreeMap/SKILLs/issues/11 | asd-ste100 script: POS-aware decision or a `homograph` finding kind |
| B18 | asd-ste100 | design question | A declared noun in the allow file also passes where the text uses it as a verb | ste100-pp, notes | open https://github.com/BTreeMap/SKILLs/issues/12 | asd-ste100 script: POS-aware allow file |
| B19 | asd-ste100 | design question | -ing technical nouns (WIRING, PARKING BRAKE) are `ing_form` findings unless allowed one by one | checker#12 | open https://github.com/BTreeMap/SKILLs/issues/13 | asd-ste100 text: -ing technical nouns go in the allow file; ste-tax allow list per task |
| B20 | asd-ste100 | design question | Number words pass before the headword lookup: "Zero the meter." never flags zero (v) | checker#13 | open https://github.com/BTreeMap/SKILLs/issues/14 | asd-ste100 script: signal a number word that is also an unapproved headword |
| B21 | asd-ste100 | design question | Meaning-only entries (GET (v) approved, get (v) "become" not) are not decidable by spelling: 39 of 42 missed | checker#14, ste100-pp | closed: rule 1.3 outside the checker; report apart | none |
| B22 | asd-ste100 | design question | Phrase match flags a verb or noun plus preposition with the same spelling ("TURN ON THE SLEEVES"): 3 STE false positives | checker#20 | open https://github.com/BTreeMap/SKILLs/issues/15 | asd-ste100 script: phrase findings for particles as signals until POS exists |
| B23 | search-web | text gap | `fetch` on a raw JSONL gave a refusal whose named causes did not apply | tasks#1 | fixed 6f9cf58 | search-web text |
| B24 | search-web | design question | No raw fetch for data files that prints SHA-256 and bytes; pinning needs curl plus sha256sum | tasks#2 | open https://github.com/BTreeMap/SKILLs/issues/16 | search-web script |
| B25 | lit-review | design question | `search` envelope gives counts only; one `show` call per round to see titles | tasks#3 | open https://github.com/BTreeMap/SKILLs/issues/17 | lit-review script: `--show` on search |
| B26 | lit-review | text gap | `show` envelope `{total, papers}` not in `schema` (L2) | tasks#4 | open https://github.com/BTreeMap/SKILLs/issues/18 | lit-review script `schema` |
| B27 | lit-review | contract gap | OpenAlex keyless allowance ends in 409s | tasks#5 | closed: environment, set BTM_OPENALEX_KEY | none |
| B28 | lit-review | design question | Lite band signal (5-10 included) fired at 12 | tasks#6 | closed: signal is advisory | none |
| B29 | lit-review | design question | Abstract-level screen excludes papers whose abstract names no benchmark | tasks#7 | closed: by design at lite; full level reads full text | none |
| B30 | lit-review | contract gap | `search --limit` capped at 100 with no offset; split by year window to reach 105 and 168 matches | research#6, notes | open https://github.com/BTreeMap/SKILLs/issues/19 | lit-review script: `--offset` or auto-page |
| B31 | lit-review | script bug | `status` drift signal persisted after the amendment | research#7 | fixed 036c1f4 | lit-review script |
| B32 | lit-review | design question | `digest` kinds are generic words ("language" 198, "english" 34) | research#8 | open https://github.com/BTreeMap/SKILLs/issues/20 | lit-review script: skip words in over ~30% of titles |
| B33 | lit-review | contract gap | `show` cannot filter by key prefix or search id | research#9, notes | open https://github.com/BTreeMap/SKILLs/issues/21 | lit-review script: `--on key` or `--found-by` |
| B34 | lit-review | text gap | Broad `screen --exclude` cut gave one reason to unlike matches | research#10 | fixed 036c1f4 | lit-review text |
| B35 | lit-review | contract gap | `status` gives one exclusion total, not split by stage; flow counts derived by grep | research#11, notes | open https://github.com/BTreeMap/SKILLs/issues/22 | lit-review script: stage field on decisions |
| B36 | lit-review | design question | Synthesize asks a full `/humanize` sweep; no minimal sweep per level | research#12 | open https://github.com/BTreeMap/SKILLs/issues/23 | lit-review text |
| B37 | lit-review | design question | No abstract fallback for paywalled chapters: 9 relevant papers excluded as inaccessible | research#13 | open https://github.com/BTreeMap/SKILLs/issues/24 | lit-review script: abstract fallback source |
| B38 | fact-check | text gap | Harness fetch timed out 4 times with no documented next step | research#1 | fixed 71d7be5 | fact-check text |
| B39 | fact-check | contract gap | Two-source rule forces `correction: null` where the owner is the only authority; 4 clear errors shipped as "needs judgment" | research#2, notes | open https://github.com/BTreeMap/SKILLs/issues/25 | fact-check verification.md Abstention |
| B40 | fact-check | design question | Report template has no slot for side findings | research#3 | open https://github.com/BTreeMap/SKILLs/issues/26 | fact-check text |
| B41 | fact-check | design question | No script renders the report from `factcheck-state.json`; 60-line renderer written in scratch | research#4 | open https://github.com/BTreeMap/SKILLs/issues/27 | fact-check `scripts/` member |
| B42 | advisor | text gap | Review template has no Routed line and no file header | research#5 | open https://github.com/BTreeMap/SKILLs/issues/28 | advisor/references/review.md |
| B43 | pl-theorist | contract gap | github-actions validation names `actionlint` and `zizmor` but no `/setup-env` tag that provisions them | harness#8 | open https://github.com/BTreeMap/SKILLs/issues/29 | pl-theorist github-actions profile |
| B44 | pl-theorist | design question | "Loads exactly one verb file" blocks a refactor-then-test chain | watermark#1, notes | open https://github.com/BTreeMap/SKILLs/issues/30 | pl-theorist text: name the chain |
| B45 | pl-theorist | text gap | `test` verb gives no way to audit laws on pre-refactor code; 35 of 83 old-code tests failed on names, not laws | watermark#2 | open https://github.com/BTreeMap/SKILLs/issues/31 | pl-theorist references/verbs/test.md step 1 |
| B46 | pl-theorist | contract gap | No mypy in the project environment; install not permitted | checker#18 | closed: record only | none |
| B47 | pl-theorist | design question | Spine (426 lines) grew to carry shared procedures | notes | open https://github.com/BTreeMap/SKILLs/issues/32 | pl-theorist text: move shared procedures to references |
| B48 | read-pdf | script bug | Lone surrogate glyph crashed `--output` with UnicodeEncodeError | watermark#3 | fixed bdfdb02 | read-pdf script |
| B49 | ponder | text gap | Explicit `"ref"` name triggers the keyword signal | watermark#4 | open https://github.com/BTreeMap/SKILLs/issues/33 | ponder text or signal |
| B50 | ponder | design question | Hedge rule unclear when a close mixes source classes: weakest or strongest source sets the hedge | watermark#5, notes | open https://github.com/BTreeMap/SKILLs/issues/34 | ponder text |
| B51 | summon | design question | One session scratchpad shared by all delegates: names collide (L4) | checker#17 | open https://github.com/BTreeMap/SKILLs/issues/35 | summon text: one scratch subdirectory per delegate |
| B52 | library | design question | Each worktree builds a new environment, 60 to 222 MB; disk dropped 1.7 to 1.5 GB (L1) | watermark#7, harness#5, notes | open https://github.com/BTreeMap/SKILLs/issues/36 | SKILLs AGENTS.md worktree note |
| B53 | library | design question | Event cap checked in the kernel and again in three members, with `<` in two and `<=` in one (L3) | notes | open https://github.com/BTreeMap/SKILLs/issues/37 | kernel: one cap check in `EventLog` |
| B54 | library | script bug | Repository gate scans Python identifiers with a per-character loop (`rules/kernel.py` line 23) | notes | open https://github.com/BTreeMap/SKILLs/issues/38 | `.github/gate` rule: one compiled pattern |
| B55 | library | script bug | Gate reflow passed an 85-column nested list item | tasks#11 | open https://github.com/BTreeMap/SKILLs/issues/39 | `.github/gate` wrap rule |
| B56 | ste-tax | design question | `.github/skills` submodule not initialized in worktrees and behind SKILLs main; sync bumps it on GitHub only | harness#6, checker#16 | open https://github.com/RadonSys/ste-tax/issues/1 | ste-tax: bump before the cluster run; CI checks out submodules |
| B57 | ste-tax | contract gap | Harness compliance matched single tokens only; multi-word terms and plurals missed | tasks#12 | fixed 04ba4d8 | ste-tax eval |
| B58 | ste-tax | contract gap | pytest and numpy were not project dependencies | watermark#6 | fixed f0d8261, 957b486 | ste-tax pyproject.toml |
| B59 | ste-tax | script bug | Blank pages and Non-STE column slack put non-STE text in STE examples | checker#15 | fixed 585fb9b | ste-tax build.py, verify.py |
| B60 | ste-tax | design question | A2 runs its own A0 draft; at temperature 0 it equals A0's output; reuse when GPU time binds | harness debt | open https://github.com/RadonSys/ste-tax/issues/2 | ste-tax eval |
| B61 | draft-paper | text gap | `init "ste-tax design plan"` signals "two or three keywords resolve best": a hyphenated keyword seems to count twice | backlog-delegate#1 | open https://github.com/BTreeMap/SKILLs/issues/40 | draft-paper text: say how a hyphenated keyword counts |
| B62 | draft-paper | design question | For `design`, claims must be noted in stage 1 for the plan to render its ledger; the `ledger` gate then re-approves the same mapping | backlog-delegate#2 | open https://github.com/BTreeMap/SKILLs/issues/41 | draft-paper text and gates: note claims before the plan gate, or merge the gates for `design` |
| B63 | draft-paper | text gap | Gate standings undefined (`open` reads as passed); after approval `next` said "finish stage 1" | backlog-delegate#3 | fixed b25cbf9 (SKILLs wt/backlog, unmerged) | draft-paper text and script |
| B64 | draft-paper | design question | `--artifacts` pinned to a worktree path that is deleted after merge; no command re-pins the root | backlog-delegate#4 | open https://github.com/BTreeMap/SKILLs/issues/42 | draft-paper script: `repin`, or a root relative to the git toplevel |
| B65 | draft-paper | text gap | Stages 0 and 1 give no path for an undecided venue or for same-week reviews that already exist | backlog-delegate#5 | open https://github.com/BTreeMap/SKILLs/issues/43 | draft-paper text: Pipeline |
| B66 | ste-tax | contract gap | `gh` token has pull only on BTreeMap/SKILLs: labels cannot be created | backlog-delegate#7 | closed: access, outside both repositories; reported to the lead | none |
| B67 | ste-tax | contract gap | Ledger fix hashes are branch hashes; main hashes differ after merge | backlog-delegate#8 | fixed ab3b85f | ste-tax docs/friction/README.md |

## Laws

An item that recurs in another skill becomes one rule or one helper.

- L1 environment: a binding isolates the skill environment from the
  caller's and states its size and location (B05, B11, B52). Home:
  author-skill `references/scripts.md`.
- L2 output contract: every JSON output shape is printed by `schema`
  and carries `schema_version`; the text names stable fields only
  (B03, B08, B12, B26). Home: author-skill standard plus a kernel
  envelope helper.
- L3 one check, one place: a kernel invariant is not re-checked in a
  member (B53). Home: kernel.
- L4 delegate isolation: parallel delegates get disjoint scratch paths
  (B51). Home: summon.
| B68 | fact-check | contract gap | No route names a read-only live probe for a claim about an API's shape or limits; the brief had to add it | verification delegate#6 | open https://github.com/BTreeMap/SKILLs/issues/44 | fact-check claims route table |
| B69 | search-web | text gap | `fetch` returned 51 characters from a JavaScript-rendered docs page with exit 0 and no signal; a weaker run reads that as empty docs | verification delegate#2 | open https://github.com/BTreeMap/SKILLs/issues/45 | search-web sources.fetch signal |
