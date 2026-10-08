# Friction ledger: backlog delegate

Skills used: draft-paper (`design`: init, schema, note, status, check).
Plus `gh` for issues. Cost = extra tool calls. SKILLs fixes: branch
`wt/backlog` in /config/repositories/SKILLs/.claude/worktrees/backlog,
not pushed.

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | draft-paper | `init "ste-tax design plan"` | Three keywords pass with no signal | `signal: 'ste-tax-design-plan': two or three keywords resolve best`. The hyphen seems to count as a split | 0 | text gap | draft-paper SKILL.md Session: say how a hyphenated keyword counts. Open |
| 2 | draft-paper | `note claim-added` in stage 1 | Template: "Stage 2 notes each as a `to-run` claim"; the plan's ledger section has no rows at the plan gate | Script admits claims in stage 1. Noted them there so `check` rendered the ledger into the plan. Then the `ledger` gate re-approves the same mapping | 1 | design question | draft-paper: for `design`, say claims are noted before the plan gate, or merge the two gates. Open |
| 3 | draft-paper | `status` gate standings | Fresh gate reads as not passed | Fresh gate shows `open`; Gates section defines no standings. After approval, `next` said "finish stage 1, then note stage-entered 2" | 1 | text gap | Fixed: SKILLs `wt/backlog` b25cbf9 (standings defined; `next` names the passed gate; 1 test) |
| 4 | draft-paper | `init --artifacts` | Root survives the merge | Root pinned to `.worktrees/backlog`; the lead deletes the worktree after merge. Later `supported` claims will resolve against a dead path, and no command re-pins the root | 0 | design question | draft-paper: a `repin` command, or root relative to a git toplevel. Open |
| 5 | draft-paper | stages 0 and 1, `design` from `shaped` | Guidance for an undecided venue and for reviews that already exist | Stage 0 says fetch the CFP and LaTeX template; stage 1 says sweep with `/lit-review`. Neither fits. Skipped both, each as a `decision` event | 1 | text gap | draft-paper SKILL.md Pipeline: venue-undecided path; reuse of a same-week review. Open |
| 6 | draft-paper | binding `$R` | Binding isolates the skill environment | Same as checker#4: binding unsets `VIRTUAL_ENV` only. Prefixed `env -u UV_PROJECT_ENVIRONMENT` by hand | 0 | contract gap | backlog B11 |
| 7 | (gh) | `gh label create -R BTreeMap/SKILLs` | Labels created (brief: write access) | HTTP 404. Token has `pull` only on SKILLs (`push`, `triage` false). Issues created without labels; class in the body | 1 | contract gap | Lead: grant triage or create labels `skill:*`, `class:*`. Open, outside the library |
| 8 | (practice) | ledger `Fixed: <hash>` | Hash findable on main | Branch hashes (3fde726, 2e84a65, 8018093, ...) differ from SKILLs main after merge (3b647e9, c02725b, 9d3db4a). Mapped by commit message | 2 | contract gap | Fixed: docs/friction/README.md, the merge hash replaces the branch hash |
