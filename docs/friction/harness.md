# Friction ledger: harness core

Skills used: pl-theorist (refactor, test, python, github-actions),
ponytail (review), asd-ste100 (check). Cost = extra tool calls.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | asd-ste100 | `check` | A way to read local `data/` or run offline: cluster egress is unknown | `check` reads only the pinned ste-tax release from a network-filled cache. No flag names a local artifact directory | 0 calls. Forced `--checker off` plus `rescore` in the harness | design question | asd-ste100 cli: `--data DIR` on `check` and `lookup` |
| 2 | asd-ste100 | `check` | Batch check for a run of 2500 texts | One process per text, about 0.45 s each with `uv run` startup. 60 texts took 18 s on 4 workers | 1 | design question | asd-ste100 cli: `check --jsonl` over many texts, one report each |
| 3 | asd-ste100 | report contract | One report schema across versions | The vendored submodule (170c269) emits no `summary` block, current main does. No schema version in the report. Read `check.py` at 170c269 to find the shared fields (`ok`, `findings[].kind`, `version`, `mode`) | 3 | contract gap | asd-ste100: `schema_version` in every report; SKILL.md "The report" names the stable fields |
| 4 | asd-ste100 | report `findings` | Count = occurrences, or count = words? | One `not_approved` item per distinct word, case folded, with a `sentences` list. Text implied it only | 1 | text gap | Fixed: SKILLs `wt/harness` 3fde726 |
| 5 | asd-ste100 | binding `uv run --project` | Know the disk cost before the first call | First call in a fresh checkout builds a `.venv` at the SKILLs workspace root (222 MB measured by the coordinator in a worktree). SKILL.md `compatibility` names uv and a full checkout, not the size | 0 (coordinator caught it) | text gap | asd-ste100 `compatibility`: state the environment size and location |
| 6 | ste-tax submodule | `.github/skills` | Submodule present and current | Not initialized in this checkout; pinned to 170c269, 6 asd-ste100 commits behind (older report, older ste-tax pin). sync-skills bumps it on GitHub only | 2 | design question | ste-tax: bump the submodule on main before the cluster run; CI checks out submodules |
| 7 | asd-ste100 | `check --mode` | A mode for short answers (math, QA) | Only `procedure` and `description`. Chose `description` for all kinds, as a flag | 0 | design question | asd-ste100 SKILL.md: say which mode fits text that is neither |
| 8 | pl-theorist | github-actions Validation | Run `actionlint` and `zizmor` | Neither installed. Did the profile's grep checks by hand (permissions, timeout, SHA pins, no `${{` in `run:`) | 1 | contract gap | pl-theorist github-actions: name the `/setup-env` tag that provisions both |

Ponytail review of the harness diff (applied):

- backends.py: yagni: `Backend` Protocol with no user. Deleted.
- harness.py: shrink: index loop for a whole-word run. Padded substring
  test, 1 line.
- harness.py: stdlib: hand-rolled mean. `statistics.fmean` plus the
  empty guard.
- net: -14 lines.

Debt:

- `ponytail:` A2 runs its own A0 draft. At temperature 0 it equals the
  A0 arm output. Reuse it when GPU time binds; latency then needs care.
- One checker process per record (row 2).
