# Task suite

Companion to docs/experiment-plan.md (Protocol). Schema: eval/README.md
and eval/records.py. One JSON object per line, fields in this order: `id`,
`kind` (`math`, `qa`, `writing`), `prompt`, `answer` (number for math,
string for qa, null for writing), `technical_terms`, `source`, `split`,
`license`. Ids are unique across all files.

## Composition

| File | Kind | Count | Source | Split | License |
| --- | --- | --- | --- | --- | --- |
| eval/tasks/gsm8k_full.jsonl | math | 1319 | GSM8K | test | MIT |
| eval/tasks/math500.jsonl | math | 200 | MATH-500 (PRM800K) | test | MIT |
| eval/tasks/nq_open.jsonl | qa | 400 | NQ-open | dev | CC BY-SA 3.0 |
| eval/tasks/writing.jsonl | writing | 26 | handwritten | writing | MIT |
| eval/tasks.jsonl | math, qa, writing | 12, 8, 2 | handwritten | starter | MIT |

- `eval/tasks.jsonl` stays at its path: the harness reads it by
  default. It is the plumbing test. Do not pool it with the benchmark
  subsets in a claim.
- Roles: `gsm8k_full.jsonl` carries the cost axis (claim 1, token
  cost). `math500.jsonl` carries the accuracy claim: GSM8K is
  saturated (docs/advisor-review.md). NQ-open stays as it is.
- Run a benchmark file with `--tasks`, for example
  `python3 -m eval run --backend vllm --model M --tasks eval/tasks/gsm8k_full.jsonl`.
- `gsm8k_full.jsonl` replaces the 400-item `gsm8k.jsonl` of the first
  build. The 400 items are a subset, byte-equal per record; the two
  files together break id uniqueness, so the old file is gone.
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
| MATH-500 (PRM800K test) | https://media.githubusercontent.com/media/openai/prm800k/7ecc794703b2877f63226f2477a49b34f9b25163/prm800k/math_splits/test.jsonl | 7ecc794703b2877f63226f2477a49b34f9b25163 | 35dc41080a3680858b27fa7e0533d2d547825316fc5dafe5d316f4ccc5a06132 | 446564 | 500 |
| NQ-open dev | https://raw.githubusercontent.com/google-research-datasets/natural-questions/fb26a3073b1fe636c97302890a27b491d6530130/nq_open/NQ-open.dev.jsonl | fb26a3073b1fe636c97302890a27b491d6530130 | f15567f38099f3615f5b8a685c0aef449c11ad90d3da3735e8d1b98115b40616 | 391316 | 3610 |

Fetched 2026-10-08. Only the samples are in the repository. The
PRM800K file is a Git LFS object: the raw URL gives a 131-byte pointer
whose `oid` is the SHA-256 above; the media URL gives the file. License
files: eval/tasks/LICENSE.gsm8k (upstream MIT text, copyright 2021
OpenAI), eval/tasks/LICENSE.math500 (PRM800K MIT text, copyright 2023
OpenAI; MATH problems, MIT), eval/tasks/LICENSE.nq-open (attribution, CC BY-SA 3.0 pointer,
list of changes). nq_open.jsonl is an adaptation under CC BY-SA 3.0;
keep it under that license.

NQ-open dev is the standard evaluation split of NQ-open; its test split
is hidden.

## Sampling

eval/tasks/build.py, standard library only:

1. Read each upstream file. Stop if its SHA-256 differs from the pin.
2. GSM8K: all 1319 lines, no draw. Gold = text after `####`, commas
   removed; integer when whole. Every gold is numeric (checked).
3. NQ-open: candidates = lines with exactly one annotated answer (2076)
   and no time-dated word in the question (`last`, `latest`, `current`,
   `currently`, `now`, `recent`, `recently`, `this year`, `today`,
   `newest`): 1959 remain. Reasons: the schema holds one gold string;
   the answers are frozen at 2018 annotation. Prompt = question + `?`.
4. MATH-500: candidates = lines whose `answer` is a plain number,
   optionally with thousands commas (318 of 500). Symbolic answers
   (fractions, radicals, tuples, intervals, degrees) leave the pool:
   the harness math check compares one number. Bias: the pool is
   slightly easier (level 5 is 24% of it, 27% of MATH-500). Prompt =
   `problem` + the math suffix. Gold = `answer` as a number.
5. NQ-open: draw 400 with
   `random.Random(0).sample(sorted(candidates), 400)`. MATH-500: draw
   200 the same way. Sort by upstream line index. Id = source, split,
   zero-padded line index (`gsm8k-test-0042`, `math500-test-0003`,
   `nq-open-dev-0123`), so each task traces to its upstream line.

Same inputs give byte-identical output (checked: two runs, same
SHA-256). Outputs, build of 2026-10-08:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| eval/tasks/gsm8k_full.jsonl | 589980 | b094951380c0ad1d8ac9a1c27134cbcc03658ee27e9b1431c66846242b6f5897 |
| eval/tasks/math500.jsonl | 81479 | 43817ea7725fa1484ae8abaa33e6c4b226763f4a543f8df5d966d5a21c78b884 |

## Regenerate

    mkdir -p /tmp/up && cd /tmp/up
    curl -sSfO https://raw.githubusercontent.com/openai/grade-school-math/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/data/test.jsonl
    curl -sSfO https://raw.githubusercontent.com/google-research-datasets/natural-questions/fb26a3073b1fe636c97302890a27b491d6530130/nq_open/NQ-open.dev.jsonl
    curl -sSf -o math500.test.jsonl https://media.githubusercontent.com/media/openai/prm800k/7ecc794703b2877f63226f2477a49b34f9b25163/prm800k/math_splits/test.jsonl
    sha256sum test.jsonl NQ-open.dev.jsonl math500.test.jsonl
    cd -
    python3 eval/tasks/build.py --gsm8k /tmp/up/test.jsonl \
      --nq-open /tmp/up/NQ-open.dev.jsonl --math500 /tmp/up/math500.test.jsonl
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
  - sd_task = 0.95: a conversion, not a measurement. Srivastava et al.
    2025 (arXiv 2511.04108, Table 5) report reasoning tokens at batch
    size 1 as 2,973 +- 190 (DeepSeek-R1) and 2,926 +- 210 (o1), 95% CI
    over n = 1,300 instances. Inverting the CI gives an sd of about
    3,500 and 3,860 tokens. Under a lognormal, the sd of log tokens is
    about 0.93 and 1.00. The lognormal conversion is the reviewer's,
    not the paper's (docs/lit-review-reasoning-cost.md). The set pools
    13 datasets, so it overstates the spread inside one benchmark.
  - The first value, 0.57, was the sd of log word count of the 1319
    GSM8K reference solutions: text written by people, not model
    output. It is the lower bound.
  - rho = 0.5: assumption, between-arm correlation of log length per
    task. No reviewed paper reports it.
  - sd of d = 0.95.
- alpha = 0.05 / 4 (Bonferroni: A1-A0 and A2-A0, two models), power
  0.8, two-sided: n = 1108 (was 399 at sd_task 0.57). Decision: the
  cost axis runs the full GSM8K test split, 1319 tasks.
- Sensitivity (eval/tasks/power.py): sd_task 0.93 needs 1062, 1.00
  needs 1228; one contrast at alpha 0.05 needs 780; rho = 0.7 needs
  665. 1319 covers each.
- Samples: each task runs k samples (default 3). The token outcome is
  the per-task mean over samples, so within-task noise drops; the
  between-task spread above does not.
- Accuracy: MATH-500 sample, n = 200 (decision). McNemar at the same
  alpha, one sample per task: power 0.36 for a 5-point drop with 8% /
  3% discordant pairs, 0.14 for a 3-point drop. k samples raise it
  only through less within-item noise. A 5-point claim at power 0.8
  needs more items: the numeric pool holds 318.
- QA uses the same rule. Its sd_task is not measured. Replace both
  assumptions with the pilot values from the first cluster run:
  `python3 eval/tasks/power.py --sd-task S --rho R`.
- Writing (26): sized by the brief, not by power. The watermark z is
  per sample; more power comes from more samples per prompt, not more
  prompts.

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

- GSM8K is defensible as the primary cost set. MATH-500 is the
  harder set and carries accuracy (added 2026-10-08, numeric answers
  only).
- Factual QA has no standard in this literature. NQ-open gives short,
  checkable answers under a permissive license. MMLU-style letter
  answers break the harness QA check (see Known limits).
- Harness budget: the default is now 16384 new tokens with the
  vendor's thinking-mode sampling (eval/README.md). 1024 with greedy
  decoding stays as a plumbing setting: it is under the 2048 budget at
  which [4] still sees truncation loss on GSM8K.

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

- Fixed in the harness refactor: naive compliance now allows a
  multi-word term whole and a term in its regular plural
  (eval/compliance.py `term_phrases`).
- GSM8K and NQ-open tasks declare no technical terms. Names of things
  (`ducks`, `muffins`) count as unapproved. Arm contrasts survive;
  absolute compliance on these sets does not.
- NQ-open gold is one string; true aliases (`U.S.` for `United States`)
  score false. Same for all arms.
- With no answer line, the harness records `fallback_correct` (gold
  found anywhere in the text) apart and never counts it as correct. A
  one-letter gold (MMLU `A`) would match almost any text. Reason
  NQ-open was used, not MMLU.

## Not done

- Pilot variance: replace sd_task and rho with measured values after
  the first cluster run.
