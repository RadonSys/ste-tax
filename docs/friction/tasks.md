# Friction ledger: task suite

One row per pain point met while building eval/tasks. Cost = extra tool
calls spent. SKILLs fixes: branch `wt/tasks` in
/config/repositories/SKILLs/.claude/worktrees/tasks, not pushed.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | search-web | `fetch` raw GSM8K JSONL URL | file text, or a refusal that names the cause | "no readable article ... may be a listing, a paywall, or rendered by JavaScript"; none applied; fell back to curl | 1 | text gap | search-web/SKILL.md fetch contract. Fixed: 5244be8 |
| 2 | search-web | `fetch` | a raw mode for data files (download with digest) | none; dataset pinning needs curl plus sha256sum outside the skill | 1 | design question | search-web scripts: optional raw fetch that prints SHA-256 and bytes. Open |
| 3 | lit-review | `search` | envelope lists hits | counts only; one `show` call per round to see titles | 1 per round | design question | lit-review: optional `--show` on search. Open |
| 4 | lit-review | `show --fields key,abstract` | shape in `schema` | envelope `{total, papers}` not in `schema`; first parse guessed `records` and failed | 1 | text gap | lit-review `schema` output: add the show envelope. Open |
| 5 | lit-review | `search --source openalex` | works keyless at low volume | worked; signal: keyless allowance, then 409s | 0 | contract gap (known) | environment: set BTM_OPENALEX_KEY. Known since 2026-02-13 |
| 6 | lit-review | `update` (screen) | lite band fits a two-round session | 12 included, signal: above lite band 5-10; disclosed in docs/tasks.md | 0 | design question | none; signal is advisory |
| 7 | lit-review | lite screen at abstract level | abstracts name benchmarks | 13 of 25 arXiv abstracts named none; excluded at lite, so the suite count undercounts | 0 | design question | none at lite; full level reads full text |
| 8 | asd-ste100 | `check` report, `findings[].` | field `word` (SKILL.md: "gives the word") | field is `token`; first print showed no words | 1 | text gap | asd-ste100/SKILL.md report section. Fixed: 87b2175 |
| 9 | asd-ste100 | `lookup` | entry fields documented | `status` is an object holding `kind`, `meaning`, `alternatives`; shape learned by trial | 1 | text gap | asd-ste100/SKILL.md lookup bullet or a `schema` verb. Open |
| 10 | asd-ste100 | `check` on two sample answers | declared part names suffice | not ok: materials and quantities (oil, air, pressure, temperature, tube) are not dictionary words; terms widened on all 26 tasks | 3 | design question | eval/tasks/writing.jsonl (done). asd-ste100 TN step 1 lists materials but not physical quantities. Open |
| 11 | SKILLs gate | `btm-repo-gate fix` | reflow a nested list item over 76 columns (AGENTS.md: gate reflows list items) | 85-column nested item passed "repository conventions hold"; reflowed by hand | 2 | script bug | .github/gate reflow rule: nested list items. Open |
| 12 | (harness, not a skill) | `compliance()` in eval/harness.py | multi-word technical terms allowed | matches single tokens only; `INNER TUBE`, plurals never match | 0 | contract gap | eval/harness.py, harness delegate. Reported |
