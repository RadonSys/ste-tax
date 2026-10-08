# Design plan

Stage 1 deliverable of `/draft-paper design`, session
`ste-tax-design-plan-pl6th4fkjo7vg9nijnm8ubb66c` (verb `design`, state
`shaped`, format `full`, model `claude-fable-5-1`). Venue: NSDI 2027 or a
measurement venue, to be decided. No CFP fetched; no venue fact below.
Brief: docs/design.md, intervention-pin.md, experiment-plan.md,
advisor-review.md, lit-review.md, lit-review-cnl.md,
lit-review-reasoning-cost.md, checker-validation.md, tasks.md.

Nothing here is a result. Every number marked "assumed" is for the
arithmetic only. Measured numbers name their source doc.

## Scenario sketch

A maintenance-manual team must ship procedures in ASD-STE100 Issue 9. It
drafts them with an open reasoning model, Qwen3.8-27B (BF16, 55.6 GB) on
one AMD MI350X, thinking on. The system prompt says "write in STE" and
attaches the 879 approved `WORD (pos)` ids: 11,893 characters, about
3,000 prompt tokens (estimate: characters / 4; tokenizer not run). The
same model also answers checkable questions in STE. Question for the
team: per request, how many more reasoning tokens, output tokens, and
seconds does STE cost, does accuracy drop, and does the output pass the
checker gate?

Workload (docs/tasks.md): 400 GSM8K test items, 400 NQ-open dev items, 26
technical-writing tasks (14 procedures, 12 descriptions). Smaller rung:
Qwen3.5-9B, same tokenizer (248,320 tokens) and thinking switch.

Present failure: nobody knows the price. Three reviews (2026-10-08) find
no paper that measures reasoning-token cost under a controlled-vocabulary
output constraint (lit-review.md Gaps; lit-review-cnl.md Summary;
lit-review-reasoning-cost.md Gaps).

## Contradiction

STE exists to make text simpler: short sentences, 879 approved word entries, one
meaning per word. Simpler output should be cheaper to produce. But a
model that must avoid its preferred words has to search for approved
ones. On a reasoning model that search can happen in the think segment,
which the reader never sees and the deployer pays for. Context moves
reasoning tokens by large factors on a fixed model (decoys up to 46x,
batching -76%; lit-review-reasoning-cost.md [2], [4]). Two things that
should agree and may not: simplicity of the output text, and cost of
producing it.

Skeptic's position (H0): STE is a surface rewrite. Reasoning stays
fixed; only output length changes, by circumlocution.

## Problem statement

- What: measure the inference cost, the accuracy, and the watermark
  effect of asking a current open reasoning model to write in STE.
- Today: STE studies test conformance (SpeciaLex, Issue 7 lexicon,
  lit-review-cnl.md [8]) or fine-tune for it ([3]). None reports a cost
  measure. Constrained-decoding studies report latency, not reasoning
  tokens (lit-review.md).
- New: a paired, arm-separated measurement. A2 (post-hoc rewrite on a
  frozen draft) holds reasoning fixed and isolates the compliance tax;
  A1 (prompt instruction) adds any thinking tax. A validated checker
  (docs/checker-validation.md) makes "STE output" checkable.
- Who cares: STE-mandated documentation teams adopting LLMs; anyone who
  puts a controlled language or style guide in a system prompt. If the
  tax is real, a style constraint is a compute line item, and A2 versus
  A1 says which path is cheaper.

## Falsifiable claims

Thesis: an output vocabulary constraint is a reasoning-cost constraint,
not only a surface one.

| # | Claim | What proves it wrong |
| --- | --- | --- |
| C1 | A1 raises think-segment tokens over A0 on the same tasks by 10% or more on Qwen3.8-27B | Paired log-ratio CI (alpha 0.05/4, bootstrap) covers zero and its upper bound is under log 1.05, while A1 compliance under gate row 4 is above A0 |
| C2 | A2 isolates a compliance tax: the rewrite pass costs tokens and seconds beyond A0 at equal accuracy | A2 total cost inside the A0 CI at equal accuracy and compliance (the pin's stop rule: H0 wins, stop) |
| C3 | STE lowers task accuracy (A1 vs A0) | McNemar difference CI covers zero at both sizes on GSM8K plus a MATH-500 subset |
| C4 | The tax changes with model size (27B vs 9B) | The two sizes' C1 CIs overlap fully, or the sign of A1-A0 differs across task families. Two points give a sign, not a trend |
| C5 | The tax lives in reasoning, not only in circumlocution | With thinking on, the A1-A0 think-token CI covers zero while the final-text token delta is positive; or the thinking-off A1-A0 delta equals the thinking-on total delta |
| C6 | A fixed vocabulary weakens KGW watermark detection | A1 z-scores at matched length inside the A0 CI (gamma 0.25, delta 2.0) |
| C7 | The checker gate ranks arms as humans do | Arm order under gate row 4 flips against human labels on a 100-output sample |

## Worked numerical example

Task `gsm8k-test-0000` (Janet's ducks, gold 18). Token counts are
assumed; prompt sizes are estimated from character counts.

| Quantity | A0 | A1 | A2 pass 1 | A2 pass 2 |
| --- | --- | --- | --- | --- |
| Prompt tokens (system + user) | 95 | 3,060 + 95 = 3,155 | 95 | 3,060 + 35 + 120 = 3,215 |
| Think tokens | 600 | 660 | 600 (= A0 draft) | 200 |
| Final-text tokens | 120 | 150 | 120 | 140 |
| Generated tokens | 720 | 810 | 720 | 340 |

Per-task arithmetic:

1. A1 thinking tax: d = ln(660 / 600) = 0.0953 = ln 1.10. This task sits
   exactly at the smallest effect the plan detects.
2. A1 generated tax: 810 - 720 = +90 (+12.5%). Circumlocution share: 30
   of 90 (final text); reasoning share: 60 of 90.
3. A2 compliance tax: pass 2 = 340 generated + 3,215 prefill. A2 total
   generated = 720 + 340 = 1,060, +47% over A0. A2 accuracy is A0's
   (frozen draft) unless pass 2 edits the answer line, which is flagged.
4. Prefill: A1 adds 3,060 prompt tokens per call. With prefix caching,
   the 3,060-token system prefix is computed once per server; each later
   call pays about 95. Report both (advisor claim 6).

Over 400 tasks (docs/tasks.md power argument):

- sd of d = sd_task x sqrt(2(1 - rho)) = 0.57 x sqrt(2 x 0.5) = 0.57.
  sd_task 0.57 measured on GSM8K reference solutions; rho 0.5 assumed.
- SE of mean d = 0.57 / sqrt(400) = 0.0285. delta / SE = 0.0953 / 0.0285
  = 3.34 = z(1 - 0.0125/2) + z(0.8) = 2.498 + 0.842. Power 0.80, n = 399.
- If sd_task = 0.93 (derived from DeepSeek-R1 CIs,
  lit-review-reasoning-cost.md [2]) at rho 0.5: n = 1,062. Power at
  n = 400: SE 0.0465, delta / SE 2.05, power about 0.33. The pilot (E0)
  decides which holds.

Compute per model (upper bound, assumed 3,000 generated tokens per call,
near R1's 2,973 mean in [2]): (826 tasks) x (k = 4) x (A0 + A1 + 2 A2
calls = 4 calls) = 13,216 calls, about 40M generated tokens. GPU-hours
unknown until E0 measures throughput.

## Experiment plan

Common settings: vLLM on one MI350X, BF16, vendor thinking sampling
(temperature 1.0, top_p 0.95, top_k 20; Qwen3.8-27B card via
advisor-review.md), budget 32,768 new tokens, k = 4 samples, prefix
caching off and on (two numbers), gate row 4 of checker-validation.md
with a per-task allow list. Arm order A0, A2, A1 (pin).

| Exp | What runs | Baseline it kills | Deciding metric | Budget | Failure criterion |
| --- | --- | --- | --- | --- | --- |
| E0 pilot | 40 tasks (seed 0), A0 and A1, 27B, k = 4 | none; sets n | sd_task, rho, truncation rate, tokens/s | about 1/20 of E1 | Truncation over 1% at 32,768: raise the budget. Required n over 1,319: narrow C1 to one task family |
| E1 cost | 826 tasks, A0 A2 A1, 27B | H0: STE is surface only | paired log-ratio of think tokens (C1); A2 pass-2 tokens and seconds (C2) | about 40M tokens | C1 or C2 falsifier above. C2 failure stops the project per the pin |
| E2 accuracy | E1 records on GSM8K plus a MATH-500 subset (to pin under build.py) | "STE only rewords" | McNemar on correct, number-tolerant extraction | adds MATH-500 calls | C3 falsifier. Power 0.70 for a 5-point drop at n = 400; a smaller drop needs the full 1,319 |
| E3 size | E1 on Qwen3.5-9B | "the tax is a 27B artifact" | sign and CI of A1-A0 per size | about 40M tokens, MI350X | C4 falsifier |
| E4 thinking off | E1 arms A0, A1 with `enable_thinking` false, 27B | "the tax is circumlocution only" | A1-A0 generated delta, off vs on | under E1 | C5 falsifier |
| E5 watermark | 26 writing tasks, hf backend, A0 vs A1, temperature 0.7, many samples per prompt | "low entropy is not the cause" | z at matched length; mean per-token entropy per arm | held until E1 returns | C6 falsifier |
| E6 checker | 100 outputs (50 A0, 50 A1, stratified) hand-labelled against the 53 rules | "the gate measures the allow list" | arm order agreement | one person-day | C7 falsifier: arm order flips |

Three hostile objections and the experiment that answers each:

1. "The model just writes longer." E4 (thinking off) and C5.
2. "Your checker defines compliance." E6, plus the stated floor: 4.4%
   false rejects, 89.1% headword recall (checker-validation.md).
3. "Greedy 1024-token runs measure the cap." Vendor sampling, 32,768
   budget, truncation counted per arm (E0).

## Prospective evidence ledger

Rendered from `check` at the plan gate (session above). Every claim is
`to-run`; paths resolve against the repository root. Each run
writes its directory with `python -m eval run --run-id <dir name>`.
Location stays empty until the run lands.

| Claim | Claim as stated in the draft | Status | Artifact | Location | Exists |
| --- | --- | --- | --- | --- | --- |
| a1-think-tax-ojin0adbjhhktl2f1gdmbaqpmc | C1: A1 raises think-segment tokens over A0 on the same tasks by 10% or more on Qwen3.8-27B | to-run | `eval/results/e1-arms-qwen38-27b/records.jsonl` | - | no |
| a2-compliance-tax-m1rj403nbb3ljk56lso3eed59s | C2: A2 isolates a compliance tax: the rewrite pass costs tokens and seconds beyond A0 at equal accuracy | to-run | `eval/results/e1-arms-qwen38-27b/records.jsonl` | - | no |
| ste-accuracy-drop-0u7tie4cpeug0is9lurbblukcc | C3: STE lowers task accuracy (A1 vs A0) on GSM8K plus a MATH-500 subset | to-run | `eval/results/e2-accuracy/records.jsonl` | - | no |
| tax-model-size-c04fjp2ob210c72g0g1kbdni6g | C4: The tax changes with model size (Qwen3.8-27B vs Qwen3.5-9B) | to-run | `eval/results/e3-arms-qwen35-9b/records.jsonl` | - | no |
| reasoning-not-circumlocution-2lseq2a5fbu2fse421lr88lc84 | C5: The tax lives in reasoning, not only in circumlocution | to-run | `eval/results/e4-nothink-qwen38-27b/records.jsonl` | - | no |
| watermark-detection-weakens-u8sk8t87q7jjgn6919fej627go | C6: A fixed vocabulary weakens KGW watermark detection at matched length | to-run | `eval/results/e5-watermark-qwen35-9b/records.jsonl` | - | no |
| checker-human-order-pqb9160ann4mlsn3bf9cgd3aeg | C7: The checker gate (row 4) ranks arms as human labels do | to-run | `eval/results/e6-checker-human/labels.jsonl` | - | no |

## Award assessment

Threshold dimensions:

| Dimension | Check | Status and evidence |
|---|---|---|
| Correctness | Claims, proofs, and experimental logic are right. | Logic holds on paper: paired design, A2 isolates reasoning, falsifiers stated. Not yet run |
| Evidence credibility | Every load-bearing claim traces to an artifact or a verified citation. | All seven claims `to-run`. Gap statements trace to three retrieved reviews |
| Claim calibration | The scope of each claim matches the scope of its evidence. | Risk: one model family, two sizes, two benchmarks. Claims say "on Qwen3.8-27B and Qwen3.5-9B", not "LLMs" |
| Venue compliance | Format, limits, anonymization, and required statements per the CFP. | Unknown: venue undecided, no CFP fetched |

Differentiating dimensions:

| Dimension | The project's standing |
|---|---|
| Problem importance and taste | Moderate: STE is required in aerospace and defence documentation (from memory); the general case (style rules in system prompts) is everywhere |
| Distinctive insight | Strong if C1 or C5 holds: an output-surface rule priced in hidden reasoning tokens |
| Novelty or surprise | Strong: three reviews find the axis empty (lit-review.md, lit-review-cnl.md, lit-review-reasoning-cost.md Gaps) |
| Prospective reach | Moderate: method transfers to any controlled language or style guide; A2 vs A1 is a deployment choice |

Lead differentiators: novelty (empty axis), then distinctive insight.

Communication: one thesis (above) organizes the claims. Elegance: A2's
frozen draft is the one mechanism; it must be clear on page 2.

Venue currency: NSDI is systems and networking. Its currency is a real
implementation, evidence from use, practicality, explored alternatives.
This project is a measurement of model behaviour; its implementation
(harness, checker) is a tool, not the contribution. Mismatch recorded as
an evidence gap. A measurement or ML-evaluation venue spends the
currency the plan has (controlled isolation, scale by size, ablation by
thinking switch).

External variance (not scored): reasoning-cost and "overthinking" papers
are frequent in 2025-2026 (lit-review-reasoning-cost.md), so reviewers
know the metrics; the angle must stay on the constraint, not on
overthinking.

Decision:

- Blocking weaknesses: no results; absolute compliance from `ok` is not
  trustworthy (rejects 44.8% of the spec's own STE examples), so report
  gate row 4 rates with their floor; GSM8K alone is saturated (needs the
  MATH-500 subset); venue undecided.
- Lead differentiators: novelty of the axis (three reviews) and the
  reasoning-tax insight (C1, C5; artifacts in E1, E4).
- Evidence gaps: rho and sd_task unmeasured (E0; failure: n over 1,319);
  one model family (GLM-4.7-Flash as an optional third, gated on a
  gfx950 smoke test); human compliance labels (E6; failure: order flip).
- Structural implication: the contradiction and the worked example lead;
  A2's frozen-draft mechanism sits beside it; the watermark axis (C6) is
  a secondary section or a separate short paper if E5 runs late.

## Gate record

- `plan`: requested after the seven claims were noted. Presented: this
  plan, the 13 events since the last decision (stage 1 entered, 4
  decisions, 7 claims, the request), and one question: approve, revise
  with notes, or reject. Decided `approve`, reply verbatim: "approved by
  the lead on the delegate's presentation".
- `ledger`: stage 2 entered, gate requested, standing `pending`. Not
  decided. The lead decides it from the ledger above.

Session decisions (trace): format `full`; positioning from the three
existing reviews, no new sweep; venue undecided, no CFP fetched; vendor
thinking sampling, budget 32,768, k = 4.
