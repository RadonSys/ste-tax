# Friction ledger: research delegate

Skills run from /config/repositories/SKILLs (main checkout bindings).
Cost = extra tool calls spent on the pain point. Fixed rows name the
SKILLs commit on branch `wt/research`.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | fact-check | Step 0, harness fetch | vendor page text to quote | amd.com timed out 4 times (product page, press release, MI100 brochure); no documented next step; used curl + `/read-pdf`, ROCm docs, third parties | 5 | text gap | fact-check/references/verification.md, Fetching. Fixed: f3071eb |
| 2 | fact-check | Invariant 4, Abstention | correction for a clear error whose only authority is the owner (HF file size, release-note wording) | two-source rule forces `correction: null`; 4 clear errors (c-10, c-27, c-31, c-38) shipped as "needs judgment" | 0 | contract gap | verification.md Abstention: exempt quotation claims and registry-derived values when the owner is the sole primary publisher. Open (design) |
| 3 | fact-check | Step 3 report template | slot for findings beside claim verdicts | none; vLLM recipe "no AMD path" and wheel gap went into an added section | 1 | design question | fact-check SKILL.md report template: optional side-findings section. Open |
| 4 | fact-check | Step 1 state file to Step 3 report | script renders the report from `factcheck-state.json` | no script; wrote a 60-line renderer in scratch | 3 | design question | fact-check scripts/ member. Open |
| 5 | advisor | review, "Output the template alone" | slot for routed work and a file header | template has neither; SKILL.md says every verb routes work outside the lens | 0 | text gap | advisor/references/review.md: add a Routed line. Open |
| 6 | lit-review | `search --limit` | all 105 / 168 matches of a small exact-phrase query | cap 100, no offset; split by year window to reach the rest | 2 | contract gap | lit-review search: `--offset` or auto-page when total is small. Open |
| 7 | lit-review | `status` after an amendment | drift signal clears once the amendment is recorded | signal persisted on every call; amendment shape not in `schema` | 3 | script bug | lit-review corpus/curate.py cmd_status. Fixed: e6d53b4 (with 2 tests) |
| 8 | lit-review | `digest` | kinds that separate 422 candidates | top kinds "language" (198) and "english" (34): generic words; fell back to `show --match` with lookahead regex | 2 | design question | lit-review digest: skip words in more than ~30% of titles. Open |
| 9 | lit-review | `show --on` | filter by key prefix or search id | only title, abstract, venue | 1 | contract gap | lit-review show: `--on key` or `--found-by`. Open |
| 10 | lit-review | `screen --exclude` broad cut | reason fits every match | "controlled" cut tagged 8 attribute-control papers with a CL-design reason; re-decided by `update` | 2 | text gap | lit-review/references/screen.md. Fixed: e6d53b4 |
| 11 | lit-review | report flow counts | `status` splits exclusions by stage | only a total; derived the full-text count by grepping reasons | 2 | contract gap | lit-review status: a stage field on decisions. Open |
| 12 | lit-review | synthesize, `/humanize` sweep | small final check | humanize is a 40-pattern skill with 7 references; ran only its mechanical step 5 greps | 1 | design question | lit-review/references/synthesize.md: name the minimal sweep per level. Open |
| 13 | lit-review | pass 2, inaccessible papers | abstract for paywalled Springer chapters | OpenAlex, Crossref, publisher page all empty; 9 relevant-looking papers excluded as inaccessible, 2 directly on LLMs for Easy German | 3 | design question | lit-review sources: an abstract fallback (Semantic Scholar elides publisher abstracts too). Open |
