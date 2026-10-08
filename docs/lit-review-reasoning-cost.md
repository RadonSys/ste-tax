# Literature review: reasoning-token cost of instructions and output constraints

Question: how do instructions and output constraints change the
reasoning-token and output-token cost of reasoning language models
(thinking budgets, overthinking, instruction-induced length), and do any
studies report the variance of token counts across samples or tasks?

Skill: `/lit-review lite` (SKILLs library). Session
`reasoning-token-cost-bnrp4upeutel2em59t03rure6o`.

## Summary

On a fixed reasoning model, what surrounds the question moves reasoning
tokens by large factors: batching queries cut them 76%, injected decoy
problems raised them up to 46x, ill-posed questions raised them sharply,
and chain-of-thought exemplars reshaped their distribution. Explicit
length instructions work poorly: models acknowledge a token limit and keep
reasoning, or comply and lose accuracy. Thinking also changes instruction
following itself, in both directions, with exact-form constraints the
consistent loser. One paper reports confidence intervals from which a
between-task spread of reasoning tokens can be derived; it is about twice
the spread ste-tax assumes for sample size. No included paper measures the
cost of a vocabulary constraint.

## Method

Lite scoping pass, one round, as of 2026-10-08. Source: arXiv, six
fielded queries (overthinking with reasoning models; thinking budget with
tokens; instruction following with reasoning models and length; reasoning
length with variance; reasoning models with output constraints; thinking
tokens with prompt). The overthinking query is a ranked sample, 40 of 163
upstream. Criteria: reasoning-model token counts under a manipulated
instruction, constraint, budget, prompt, or difficulty, or reported token
variance; empirical; 2024 or later; English. Excluded: efficiency methods
whose token cost is the outcome of a new training or decoding method,
surveys, and serving work. Flow: 100 fetched, 97 unique, 87 excluded at
title and abstract, 10 included. Read level: 2 full text ([2], [10]), 8
abstract. Snowballing did not run (not required at lite).

## Context and instructions move reasoning tokens

On 13 benchmarks with DeepSeek-R1 and o1, batch prompting cut mean
reasoning tokens by 76% (2,950 to 710) while keeping or raising accuracy
[2]. Decoy problems injected into retrieved context raised reasoning
tokens 13x, 46x, and 12x on FreshQA, SQuAD, and MuSR with answers still
correct [4]. Questions with a missing premise drastically lengthen the
responses of reasoning models, while non-reasoning models answer short and
flag the flaw [1]. On R1-distilled models, direct prompting gives a highly
dispersed distribution of thinking tokens and few-shot exemplars
concentrate it [10]. Difficulty also sets spend: reasoning models are
poorly calibrated to optimal token count, worst on easy problems [3], and
emit about 18x more tokens than other models on basic math [5]. Four
groups agree that inputs other than the task itself change reasoning cost
by factors, not percents [1], [2], [4], [10].

## Explicit length instructions are weak levers

Explicit limits fail in the one study that tests them directly. Under
"use no more than 100 tokens for reasoning", DeepSeek-R1 still produced
1,256 reasoning tokens on Game of 24 against 2,301 at baseline (45% less),
and o1 cut tokens 17% while accuracy fell from 96% to 45% [2]. Constraining
tokens can collapse accuracy by up to about 36% [5]. When instructions
target the reasoning trace itself (language, format, length), fewer than
25% of traces comply, and compliance falls as difficulty rises [8]. Two
groups [2], [8] agree that reasoning models follow instructions about
their own reasoning poorly; [5] adds the accuracy cost of forcing it.

## Thinking and instruction following interact

Models tuned for long reasoning lose instruction adherence as generation
length grows [6]. With the same Qwen3 weights, thinking on versus off
changes IFEval pass rates by only -0.55 to -3.52 points, yet 10-20% of
prompts flip between pass and fail; constraints on exact local form get
worse under thinking, and thinking changes final-answer length, which
matched-length analysis only partly explains [7]. The same benchmark
family finds trace-level instruction following below 25% [8]. For ste-tax,
STE is an exact-local-form constraint on every word, the class [7] finds
thinking hurts.

## Variance of token counts

Reasoning-token usage fluctuates across domains and prompt styles enough
that predicting it needs per-domain calibration [9]. One paper gives
numbers: its Table 5 reports DeepSeek-R1 reasoning tokens at batch size 1
as 2,973 +- 190 and o1 as 2,926 +- 210 (95% CI over n = 1,300 pooled
instances, 13 datasets x 100) [2]. Inverting the stated CI formula gives a
between-instance sd of about 3,500 and 3,860 tokens, a coefficient of
variation of about 1.2 and 1.3. If the counts are roughly lognormal, the
sd of log tokens is about 0.93 and 1.00 (this conversion is the
reviewer's, not the paper's). The pooled set mixes 13 datasets, so this
overstates within-benchmark spread. docs/tasks.md assumes sd_task = 0.57
from GSM8K reference-solution lengths and notes that model outputs can
vary more; [2] supports that note. No included paper reports the
between-condition correlation (rho) of per-task token counts.

## Limitations of this review

One source (arXiv) and one round; OpenAlex and snowballing did not run.
Eight of 10 papers were read at abstract level. All 10 are preprints. The
broad title cut excluded several overthinking benchmarks that report token
counts under difficulty alone; the shortlist favours manipulated
instructions. The variance figure rests on one paper and on a
distributional assumption.

## Gaps and open questions

- None of the 10 included papers measures the reasoning-token cost of a
  vocabulary or controlled-language constraint on the output (probes s3,
  s5).
- None reports the paired correlation of per-task token counts between two
  prompt conditions, the rho that sets ste-tax's sample size (probe s4).

## Included papers

| [n] | Title | Authors | Year | Venue | Read | Key |
| --- | --- | --- | --- | --- | --- | --- |
| [1] | Missing Premise exacerbates Overthinking: Are Reasoning Models losing Critical Thinking Skill? | Fan et al. | 2025 | arXiv | abstract | arxiv:2504.06514 |
| [2] | Batch Prompting Suppresses Overthinking Reasoning Under Constraint | S. Srivastava et al. | 2025 | arXiv | full-text | arxiv:2511.04108 |
| [3] | THOUGHTTERMINATOR: Benchmarking, Calibrating, and Mitigating Overthinking in Reasoning Models | Pu et al. | 2025 | arXiv | abstract | arxiv:2504.13367 |
| [4] | OverThink: Slowdown Attacks on Reasoning LLMs | Kumar et al. | 2025 | arXiv | abstract | arxiv:2502.02542 |
| [5] | Do LLMs Overthink Basic Math Reasoning? Benchmarking the Accuracy-Efficiency Tradeoff in Language Models | G. Srivastava et al. | 2025 | arXiv | abstract | arxiv:2507.04023 |
| [6] | Scaling Reasoning, Losing Control: Evaluating Instruction Following in Large Reasoning Models | Fu et al. | 2025 | arXiv | abstract | arxiv:2505.14810 |
| [7] | When Built-in Thinking Helps and Hurts: Constraint-Level Error Shifts in Instruction Following | Senthil Kumar | 2026 | arXiv | abstract | arxiv:2606.09662 |
| [8] | ReasonIF: Large Reasoning Models Fail to Follow Instructions During Reasoning | Kwon et al. | 2025 | arXiv | abstract | arxiv:2510.15211 |
| [9] | Predictive Auditing of Hidden Tokens in LLM APIs via Reasoning Length Estimation | Wang et al. | 2025 | arXiv | abstract | arxiv:2508.00912 |
| [10] | Innate Reasoning is Not Enough: In-Context Learning Enhances Reasoning Large Language Models with Less Overthinking | Ge et al. | 2025 | arXiv | full-text | arxiv:2503.19602 |
