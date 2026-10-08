# Friction ledgers

Each task that runs a skill keeps one ledger here: `<task>.md`. A pain
point met while the task runs is one row. Write it when it happens, not
from memory at the end.

Row shape:

| # | Skill | Verb or command | Expected | Happened | Cost | Class | Fix location |
| --- | --- | --- | --- | --- | --- | --- | --- |

- Cost: extra tool calls spent on the point.
- Class: `script bug`, `text gap`, `contract gap`, `design question`.
- Fix location: a skill's script, its text, author-skill's standard, the
  kernel, or ste-tax. Write `Fixed: <commit>` when fixed.

Where fixes land:

- Small decidable fix in a skill: SKILLs worktree branch, one commit,
  hash in the row. The lead merges. Never edit `.github/skills`.
  After the merge, the hash on main replaces the branch hash.
- ste-tax fix: ste-tax branch, same rule.
- Design question or large fix: leave open. It goes to backlog.md and to
  a GitHub issue (BTreeMap/SKILLs for library items, RadonSys/ste-tax
  for repository items).

Law extraction. Before a fix, ask: would this recur in another skill? If
yes, the fix is a rule in author-skill or a kernel helper, not a
one-skill patch. Record the law in backlog.md "Laws" and link each row
it covers.

backlog.md merges all ledgers: one row per distinct item, with the
ledgers that reported it, status (fixed commit, open issue, or closed
with reason), and home. Rebuild it after each wave.
