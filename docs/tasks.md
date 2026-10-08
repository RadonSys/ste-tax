# Task suite

Companion to docs/experiment-plan.md (Protocol). Schema and harness:
eval/harness.py. One JSON object per line, fields in this order: `id`,
`kind` (`math`, `qa`, `writing`), `prompt`, `answer` (number for math,
string for qa, null for writing), `technical_terms`, `source`, `split`,
`license`. Ids are unique across all files.

## Composition

| File | Kind | Count | Source | Split | License |
| --- | --- | --- | --- | --- | --- |
| eval/tasks/gsm8k.jsonl | math | 400 | GSM8K | test | MIT |
| eval/tasks/nq_open.jsonl | qa | 400 | NQ-open | dev | CC BY-SA 3.0 |
| eval/tasks/writing.jsonl | writing | 26 | handwritten | writing | MIT |
| eval/tasks.jsonl | math, qa, writing | 12, 8, 2 | handwritten | starter | MIT |

- `eval/tasks.jsonl` stays at its path: the harness reads it by
  default. It is the plumbing test. Do not pool it with the benchmark
  subsets in a claim.
- Run a benchmark file with `--tasks`, for example
  `python eval/harness.py --backend vllm --model M --tasks eval/tasks/gsm8k.jsonl`.
- Writing tasks: 14 procedures (`techwrite-pNN`, numbered steps) and 12
  descriptions (`techwrite-dNN`, no instructions). Domains: vehicles,
  workshop tools, home systems, electrical safety, one aircraft system.
  Unscored. They feed compliance, cost, and the watermark runs.
- Math and QA prompts end with the answer-line instruction of the starter
  set (`Answer: <number>` or `Answer: <value>`).

## Upstream files

| Name | URL | Commit | SHA-256 | Bytes | Lines |
| --- | --- | --- | --- | --- | --- |
| GSM8K test | https://raw.githubusercontent.com/openai/grade-school-math/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/data/test.jsonl | 3101c7d5072418e28b9008a6636bde82a006892c | 3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14 | 749738 | 1319 |
| NQ-open dev | https://raw.githubusercontent.com/google-research-datasets/natural-questions/fb26a3073b1fe636c97302890a27b491d6530130/nq_open/NQ-open.dev.jsonl | fb26a3073b1fe636c97302890a27b491d6530130 | f15567f38099f3615f5b8a685c0aef449c11ad90d3da3735e8d1b98115b40616 | 391316 | 3610 |

Fetched 2026-10-08. Only the samples are in the repository. License
files: eval/tasks/LICENSE.gsm8k (upstream MIT text, copyright 2021
OpenAI), eval/tasks/LICENSE.nq-open (attribution, CC BY-SA 3.0 pointer,
list of changes). nq_open.jsonl is an adaptation under CC BY-SA 3.0;
keep it under that license.

NQ-open dev is the standard evaluation split of NQ-open; its test split
is hidden.

## Sampling

eval/tasks/build.py, standard library only:

1. Read each upstream file. Stop if its SHA-256 differs from the pin.
2. GSM8K: candidates = all 1319 lines. Gold = text after `####`, commas
   removed; integer when whole. Every gold is numeric (checked).
3. NQ-open: candidates = lines with exactly one annotated answer (2076)
   and no time-dated word in the question (`last`, `latest`, `current`,
   `currently`, `now`, `recent`, `recently`, `this year`, `today`,
   `newest`): 1959 remain. Reasons: the schema holds one gold string;
   the answers are frozen at 2018 annotation. Prompt = question + `?`.
4. Draw 400 with `random.Random(0).sample(sorted(candidates), 400)`.
   Sort by upstream line index. Id = source, split, zero-padded line
   index (`gsm8k-test-0042`, `nq-open-dev-0123`), so each task traces to
   its upstream line.

Same inputs give byte-identical output (checked: two runs, same
SHA-256).

## Regenerate

    mkdir -p /tmp/up && cd /tmp/up
    curl -sSfO https://raw.githubusercontent.com/openai/grade-school-math/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/data/test.jsonl
    curl -sSfO https://raw.githubusercontent.com/google-research-datasets/natural-questions/fb26a3073b1fe636c97302890a27b491d6530130/nq_open/NQ-open.dev.jsonl
    sha256sum test.jsonl NQ-open.dev.jsonl
    cd -
    python3 eval/tasks/build.py --gsm8k /tmp/up/test.jsonl --nq-open /tmp/up/NQ-open.dev.jsonl
    python3 eval/tasks/validate.py
    git diff --stat eval/tasks   # empty when the sample is unchanged

`validate.py` checks field order, types per kind, non-empty strings,
and id uniqueness over eval/tasks.jsonl and eval/tasks/*.jsonl. Exit 1
on any error.

## Size: power argument

Primary outcome: token cost. Per task, d = log(tokens, arm X) -
log(tokens, A0). Same tasks in both arms, so the test is paired.

- Effect to detect: 10% change in generated tokens, delta = log 1.10 =
  0.095. Smaller than every effect in the reviewed work: concise CoT
  prompting cut length by 48.70% [1]; compression methods cut 40-67%
  [7] [8]. A 10% STE tax is the smallest effect worth a claim.
- Variance: sd of d = sd_task x sqrt(2(1 - rho)).
  - sd_task = 0.57: measured, sd of log word count of the 1319 GSM8K
    reference solutions. A proxy for how much length varies with the
    problem. Model outputs can vary more.
  - rho = 0.5: assumption, between-arm correlation of log length per
    task. Same-task pairs usually correlate more; 0.5 is conservative.
    No reviewed abstract reports a per-task variance.
  - sd of d = 0.57.
- alpha = 0.05 / 4 (Bonferroni: A1-A0 and A2-A0, two models), power
  0.8, two-sided: n = 399. Run 400.
- Sensitivity (eval/tasks/power.py): one contrast at alpha 0.05 needs
  281; rho = 0.7 needs 240.
- Accuracy (McNemar, n = 400, same alpha): power 0.70 for a 5-point
  drop with 8% / 3% discordant pairs; 0.31 for a 3-point drop. Small
  accuracy losses need the full 1319 GSM8K test split. The run cost is
  low; extend with `random.Random(0)` order kept, or run the full file.
- QA uses the same n. Its sd_task is not measured; QA answers are short,
  so think-segment length dominates. Replace both assumptions with the
  pilot values from the first cluster run: `python3 eval/tasks/power.py
  --sd-task S --rho R`.
- Writing (26): sized by the brief, not by power. The watermark z is
  per sample; more power comes from more samples per prompt at
  temperature 0.7, not more prompts.

## Benchmark choice: what cost and verbosity studies use

Lite review, run with /lit-review on 2026-10-08. Question: which task
suites do studies of reasoning-token cost, output length, and verbosity
use to measure cost and accuracy together. Searches: arXiv (s1, 373
matches, top 25) and OpenAlex from 2023 (s2, 1643 matches, top 20). Both
are ranked samples. 44 screened on abstract, 12 included (above the
lite band of 5-10). All read at abstract level only; a benchmark named
only in a full text is missed.

- GSM8K is the most frequent grade-school math suite, nearly always
  with a harder set, MATH-500 or AIME [9] [7] [6] [8] [4] [11].
- MATH-500 and AIME are the standard harder sets for the length and
  accuracy trade-off [9] [7] [6] [10] [3] [2].
- Knowledge and multiple-choice QA (MMLU-Pro, GPQA, an MCQA set, five
  knowledge QA sets) appear as secondary or out-of-domain suites [5]
  [7] [1] [12].
- On GSM8K and MATH-500, Qwen3 non-thinking mode matches or beats
  thinking mode at every output budget up to 2048 tokens: long traces
  crowd out the answer [4].
- No included study measures output cost on technical writing. Gap
  probes: s1, s2.

Consequences for this suite:

- GSM8K is defensible as the primary reasoning set. A harder set
  (MATH-500) is the expected second set. Not added: no MATH-500 file
  was pinned in this pass; see Not done.
- Factual QA has no standard in this literature. NQ-open gives short,
  checkable answers under a permissive license. MMLU-style letter
  answers break the harness QA check (see Known limits).
- Harness budget: `max_new_tokens` 1024 with thinking on is under the
  2048 budget at which [4] still sees truncation loss on GSM8K. Count
  truncated outputs per arm, or raise the budget.

References (read level: abstract):

- [1] The Benefits of a Concise Chain of Thought on Problem-Solving in
  Large Language Models. 2024. doi:10.1109/fllm63129.2024.10852493
- [2] Token Budget Saturation and Mechanistic Early Detection of
  Reasoning Non-Convergence in Chain-of-Thought Models. 2026.
  arXiv:2607.21433
- [3] BadThink: Triggered Overthinking Attacks on Chain-of-Thought
  Reasoning in Large Language Models. 2025. arXiv:2511.10714
- [4] The Coupling Tax: How Shared Token Budgets Undermine Visible
  Chain-of-Thought Under Fixed Output Limits. 2026. arXiv:2605.07686
- [5] Length Penalties Make Chain-of-Thought Less Monitorable. 2026.
  arXiv:2607.09786
- [6] Let LRMs Break Free from Overthinking via Self-Braking Tuning.
  2025. arXiv:2505.14604
- [7] Reconsidering Overthinking: Penalizing Internal and External
  Redundancy in CoT Reasoning. 2025. arXiv:2508.02178
- [8] Activation Steering for Chain-of-Thought Compression. 2025.
  arXiv:2507.04742
- [9] Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like
  LLMs. 2024. arXiv:2412.21187
- [10] Walk Before You Run! Concise LLM Reasoning via Reinforcement
  Learning. 2025. arXiv:2505.21178
- [11] Pay for Hints, Not Answers: LLM Shepherding for Cost-Efficient
  Inference. 2026. doi:10.48550/arxiv.2601.22132
- [12] Verbosity ≠ Veracity: Demystify Verbosity Compensation Behavior
  of Large Language Models. 2024. doi:10.48550/arxiv.2411.07858

## Technical terms in writing tasks

Each writing task declares names of parts, systems, materials,
physical quantities, and units. Method:

- Draft terms from the prompt.
- Write a sample STE answer for techwrite-p05 (procedure) and
  techwrite-d01 (description). Check each with the asd-ste100 skill
  (`check`, mode per task). First pass: not ok. Undeclared: `engine`,
  `oil` (p05); `air`, `pressure`, `temperature`, `tube`,
  `compartment` (d01). Words like these are technical nouns, not
  dictionary words.
- Add materials and quantities to all 26 tasks. Both samples then pass
  (`ok: true`). Remaining signals were part-of-speech candidates, each
  read and correct.
- `lookup` over every word in every term (218 words). Removed: `BASE`
  and `STROKE` (unapproved nouns with alternatives `bottom`, `travel`),
  `MAIN SWITCH` (became `ISOLATOR SWITCH`), `BLEED` (approved verb).
  Kept as item names: `RESIDUAL CURRENT DEVICE`, `ROUND FILE`,
  `STATIC PORT`.

Two of 26 sample answers were checked. The rest rely on the same term
classes.

## Known limits

- Harness compliance (eval/harness.py `compliance`) drops single tokens
  that equal a declared term. A multi-word term (`INNER TUBE`, `OIL
  FILTER`) never equals one token, so its words count as unapproved.
  Plurals (`TIRES`) also miss. This lowers compliance for writing tasks
  under every arm. Owner: harness.
- GSM8K and NQ-open tasks declare no technical terms. Names of things
  (`ducks`, `muffins`) count as unapproved. Arm contrasts survive;
  absolute compliance on these sets does not.
- NQ-open gold is one string; true aliases (`U.S.` for `United States`)
  score false. Same for all arms.
- Harness QA check falls back to a substring of the gold in the whole
  final text. A one-letter gold (MMLU `A`) would match almost any text.
  Reason NQ-open was used, not MMLU.

## Not done

- MATH-500 subset: the reviewed studies pair GSM8K with it. Next step
  under the same build.py discipline.
- Pilot variance: replace sd_task and rho with measured values after
  the first cluster run.
