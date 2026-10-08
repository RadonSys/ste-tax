# Friction ledger: reconcile delegate

Wave 2. Skills used: asd-ste100 (`check`, `lookup`, `review` on
docs/runbook.md), fact-check (its report as input). Cost = extra tool
calls. SKILLs fix: branch `wt/reconcile` in
/config/repositories/SKILLs/.claude/worktrees/reconcile, not pushed.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | asd-ste100 (harness binding) | `python -m eval run` with `--checker cli` under `UV_PROJECT_ENVIRONMENT` | Checker runs in the SKILLs environment | `CheckerCli` unset only `VIRTUAL_ENV`. First mock run installed btm-asd-ste100, btm-corekit, pydantic, httpx into ste-tax's `.venv` (same cause as docs/friction/checker.md row 4). Left in place: `uv sync` is outside the brief | 1 | script bug | Fixed: ste-tax 753e7c5 (`CheckerCli` unsets `UV_PROJECT_ENVIRONMENT`) |
| 2 | (ste-tax) | `scripts/checker_validation.py` detail file, key `h` | H list on disk | Detail file lived in gitignored `eval/results/` of a removed worktree. Reran the validation: 3,855 calls, 8 min. Same tables (93 tokens, 4.4%, 89.1%) | 2 | contract gap | Fixed: ste-tax 753e7c5 (`eval/gate_h.json` committed); AGENTS.md release step 6 |
| 3 | asd-ste100 | `lookup examples` | Entry EXAMPLE (n), since `check` passes "examples" | `entries: []` and `next: "not in the dictionary"`. The dictionary prints no plurals; `lookup` did not read the lexicon's derived plurals. `lookup tests` showed test (v) only, not TEST (n) | 1 | script bug | Fixed: SKILLs `wt/reconcile` f568d5d (cli.py `by_plural`, 2 tests, SKILL.md lookup bullet) |
| 4 | asd-ste100 | `review` of a list of questions | A form for a question in STE | "What", "question", "answer" are not in the dictionary. Rewrote section 0 as noun phrases | 1 | design question | asd-ste100 SKILL.md "Write STE": say how to write a question (WHICH, HOW, a noun phrase). Open |
| 5 | asd-ste100 | `review`, computing nouns | "run", "job", "process", "file", "log" pass as technical nouns | Each is an unapproved headword (run (v), job (n), process (n), file (v), log (v)). An allowed noun also passes the verb (SKILL.md says so). Renamed "smoke run" to "smoke test", "run log" to "log"; kept job, process, file, log in the allow file | 2 | design question | asd-ste100: part-of-speech-aware allow terms (`job (n)`), as docs/friction/checker.md row 11. Open |
| 6 | asd-ste100 | binding `$R` vs the brief | One uv rule | Brief: run uv only as `UV_PROJECT_ENVIRONMENT=<ste-tax>/.venv uv run`. SKILL.md binding: `env -u VIRTUAL_ENV uv run --project <skill>/scripts`, which uses the SKILLs `.venv`. Followed the binding (no new environment); the brief's form would install the skill into ste-tax | 0 | contract gap | Coordinator brief: name the skill binding as the exception, with `-u UV_PROJECT_ENVIRONMENT` |
| 7 | fact-check | report, "Corrections as old-span / new-span pairs" | Spans that match the file | Spans join wrapped lines with two spaces ("The  newest production release"); a literal match fails. Matched with whitespace-insensitive search | 1 | text gap | fact-check report template: keep the line break, or say a double space marks one |
| 8 | (upstream data) | `curl` PRM800K `math_splits/test.jsonl` raw URL | The 446,564-byte file | A 131-byte Git LFS pointer. The pointer's `oid` is the SHA-256; the file comes from media.githubusercontent.com | 1 | contract gap | docs/tasks.md (done): URL table names the media URL and the pointer |

STE review result for docs/runbook.md (`check --format markdown --mode
procedure --allow:file docs/runbook.terms.txt`, SKILLs b663ba1):

- First pass, no allow file: 77 `not_approved`, 2 `ing_form`, 3
  `sentence_length` after the allow file. Fixed in text: "run" (v) to
  "operate", "copy" (v) to "put a copy", "stage" to "get", "exact" to
  "full", "Size" to "GB", "Purpose" to "Function", "default" rephrased,
  questions to noun phrases, 3 long sentences divided, "the egress is
  not known" (passive) and "Do the check and get" (two instructions)
  rewritten.
- Last pass: `ok: true`, 0 findings. 14 `part_of_speech` signals, each
  read: every one is the approved part of speech (nouns after an
  article, verbs after a subject). Sections 3 and the introduction also
  pass in `description` mode.
- Allow file: names, persons, and items of the computer work, each
  looked up first. `job`, `process`, `file`, `log` are unapproved
  headwords kept as technical nouns (row 5).
