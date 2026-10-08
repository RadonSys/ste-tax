# Friction ledger: watermark delegate

Cost = extra tool calls spent on the pain point.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | pl-theorist | kernel, Verbs: "loads exactly one verb file" | One run covers refactor plus its law tests | Rule forbids two verb files; ran refactor, then test, as two passes | 0 | design question | pl-theorist/SKILL.md Verbs: name refactor-then-test as an allowed chain, or say the test verb follows refactor's step 5 |
| 2 | pl-theorist | test, step 5 "a failing law test is a finding" | Way to run new law tests against the pre-refactor code | New API (Scheme, NamedTuple, truncate_matched) made 35 of 83 old-code tests fail on names, not laws; needed a scratch shim and a separate audit script | 4 | text gap | pl-theorist/references/verbs/test.md step 1: audit laws on the old code with a throwaway script before the refactor changes the API; separate API errors from law failures |
| 3 | read-pdf | `$R <pdf> --output <file>` | Exit 0, or a documented exit 1 or 2 | UnicodeEncodeError traceback on lone surrogate `\ud835`, partial file | 2 | script bug | Fixed: SKILLs branch wt/watermark, commit 0791e4d (render.py `scalar_text`) |
| 4 | ponder | `note` source with `"ref": "uwbench"` | `ref` names the ID, per SKILL.md | `signal: 'uwbench': two or three keywords resolve best` | 0 | text gap | ponder/SKILL.md or the signal: exempt explicit `ref` names, or say refs follow the keyword rule too |
| 5 | ponder | `check` after one round | Hedge advisory for claims resting on one `measured` source (S2, S3) | `hedges: []`; joint closes with an attested source hide the single-measured leaf | 0 | design question | ponder hedge rule: say whether a close's weakest or strongest source sets the hedge |
| 6 | (ste-tax) | `uv run pytest tests/test_watermark.py` (brief) | Tests run | pytest and numpy are not project dependencies; used `uv run --with pytest --with numpy pytest ...` | 1 | contract gap | ste-tax pyproject.toml dev group (harness-core owner) |
| 7 | (disk) | SKILLs worktree `uv run --all-packages pytest` | Reuse of the main checkout venv | New 222 MB .venv in the worktree; free disk 1.7 to 1.5 GB; deleted after commit; gate fixer skipped to stay above 1.2 GB | 2 | design question | SKILLs AGENTS.md worktree note: point `UV_PROJECT_ENVIRONMENT` at the main venv |
