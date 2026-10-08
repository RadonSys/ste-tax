# Advisor review: ste-tax as a research artifact

Skill: `/advisor review` (SKILLs library), run 2026-10-08 on docs/design.md,
docs/intervention-pin.md, docs/experiment-plan.md, docs/dcs-amd-hardware.md,
docs/lit-review.md. Read-only. Sources retrieved this run carry a date;
"from memory" marks the rest (model cutoff June 2026).

## Constitution
ASD-STE100 as LLM output target (transferred) + verifiable-instruction evaluation (tweaked) + draft-then-enforce (tweaked) + overthinking token metrics (transferred) + green-list watermark (as-is) + low-entropy watermark failure (transferred) + lexicon compliance checker [new]. Patterns: Measurement, Transfer, Composition.
- Output target: ASD-STE100 Issue 9 (ASD, 2025-01-15), a controlled language written for human technical writers. Tag: transferred (from human documentation practice to LLM generation).
- A1 prompt instruction with the approved-word list attached: verifiable-instruction evaluation, IFEval (Zhou et al. 2023, from memory; not in docs/lit-review.md). Tag: tweaked (the instruction is an 879-entry lexicon, not a format rule).
- A2 post-hoc rewrite with frozen draft: draft-then-enforce, draft-conditioned constrained decoding (Reddy et al. 2026, arXiv:2603.03305, lit-review [18]). Tag: tweaked (enforcement by a second prompted pass, not by a decoding mask).
- Reasoning-token cost from the `<think>` span: overthinking efficiency metrics (Chen et al., arXiv:2412.21187, published 2024-12-30, retrieved 2026-10-08). Tag: transferred (cost driver moves from problem difficulty to an output constraint).
- Green-list watermark, gamma 0.25, delta 2.0, z-score at matched length: Kirchenbauer et al. 2023 (lit-review [13]). Tag: as-is.
- Prediction that a fixed vocabulary weakens detection: low-entropy watermark studies (lit-review [6], [8], [11]). Tag: transferred (from code and math text to controlled-vocabulary prose).
- Compliance checker: trie over data/lexicon.json built from the spec. Tag: new for LLM evaluation; commercial STE checkers for human writers exist (from memory).
- Thinking-off control via `enable_thinking`: vendor switch (Qwen3.8-27B card, retrieved 2026-10-08). Tag: as-is.
- Size contrast, Qwen3.8-27B vs Qwen3.5-9B, one tokenizer: two-point scaling probe. Tag: as-is.

## Setup
| element | paper | current practice | class | source |
| --- | --- | --- | --- | --- |
| scale | 22 starter tasks, 1 greedy sample per task and arm | hundreds of items per benchmark; reasoning models reported as avg@k over sampled runs | toy | Qwen3.8-27B card reports "avg@3", retrieved 2026-10-08, huggingface.co/Qwen/Qwen3.8-27B |
| models | Qwen3.8-27B (2026-08-05), Qwen3.5-9B (2026-02-27), open weights | newest open dense reasoning checkpoints that fit one GPU | current | HF API createdAt, retrieved 2026-10-08; docs/fact-check-hardware.md c-37, c-39 |
| hardware | 1x MI350X per run; MI100 for bring-up | MI350X is AMD's current CDNA 4 part; MI100 (2020) is outside vLLM's ROCm GPU list | current (MI350X); legacy (MI100) | ROCm docs 10.1.0, vLLM gpu.rocm docs, retrieved 2026-10-08; fact-check c-01, c-47 |
| substrate | vLLM 0.23.0 on ROCm 7.14.0 | ROCm 10.1.0 (2026-10-05) ships vLLM 0.29.0; vLLM upstream v0.31.0 (2026-10-05) | legacy | rocm.docs.amd.com release history; GitHub vllm-project/vllm releases; retrieved 2026-10-08 |
| decoding | temperature 0, seed 0, max 1024 new tokens, thinking on | vendor thinking-mode sampling `temperature=1.0, top_p=0.95, top_k=20`; reasoning budget up to 262,144 tokens | toy | Qwen3.8-27B card, "Best Practices", retrieved 2026-10-08 |
| workload | GSM8K, MMLU subsets planned; NQ-open; technical-writing prompts | GSM8K "plateaued around 95%", largely label noise; GSM8K-Platinum (relabelled GSM8K test set), MATH-500, AIME used to separate models | legacy | gradientscience.org/gsm8k-platinum, published 2025-03-06, retrieved 2026-10-08 |
| baseline | A0 free-form, same model, same tasks | the unconstrained model at its own best decoding | current (once decoding is fixed) | design reading, no external source needed |
| metric: cost | think-span tokens, generated tokens, batch-1 latency | reasoning tokens per task with outcome and process efficiency metrics | current | arXiv:2412.21187, retrieved 2026-10-08 |
| metric: compliance | naive vocabulary check, no POS, meaning, or rule check | STE conformance covers 53 writing rules plus one meaning per word | toy | docs/intervention-pin.md; data/rules.json (53 rules) |
| metric: watermark | KGW green list, hf backend only | KGW is the research baseline; SynthID-Text is the production scheme, live in Gemini | legacy (as sole scheme) | Dathathri et al., Nature, 2024-10-23, doi:10.1038/s41586-024-08025-4, Crossref retrieved 2026-10-08 |

## Envelope (assumption)
- Compute: shared access to two 8-way MI350X nodes and one 8-way MI100 node at DCS; no allocation yet; single-node, one GPU per run. Correct this if the allocation is a GPU-hour quota.
- Network: irrelevant; no multi-GPU path.
- Data: public benchmarks plus the STE Issue 9 spec under its educational grant; no private corpus.
- People: one student-month plus coding agents (assumption).
- Money: zero for rented compute or API spend; closed frontier models are out by design.

## Claims
1. A1 (prompt instruction) raises reasoning tokens over A0 on the same tasks (H1 cost core). Instrument: the real system, Qwen3.8-27B on one MI350X, vendor thinking sampling, a reasoning budget of at least 32,768 tokens so no arm truncates, k >= 4 samples per task, >= 200 checkable tasks, paired per-task difference in think tokens with a bootstrap CI. Kill test: the paired A1-A0 CI covers zero and its upper bound is under 5% of the A0 mean at both sizes, while A1 compliance is clearly above A0.
2. A2 isolates a compliance tax separate from reasoning. Instrument: A2 rewrite-pass tokens and latency on frozen drafts, answer-preservation check against the draft, same samples as claim 1. Kill test: A2 total cost within the A0 CI at equal accuracy and compliance (the pin's own stop rule).
3. STE lowers task accuracy. Instrument: an unsaturated checkable set (GSM8K-Platinum subset plus MATH-500 subset), number-tolerant answer extraction that ignores STE rewording, k samples per item. Kill test: the A1-A0 accuracy difference CI covers zero at both sizes.
4. The tax changes with model size. Instrument: the 27B/9B pair at identical settings; two points give a sign, not a trend. Kill test: the sign of the A1-A0 cost difference differs across task families, or the two sizes' CIs overlap fully.
5. A fixed vocabulary weakens watermark detection. Instrument: KGW and SynthID-Text on the hf backend, z-scores at matched length, plus mean per-token entropy per arm to test the entropy mechanism. Kill test: A1 z-scores at matched length inside the A0 CI for both schemes.
6. A1 measures "the realistic deployment path" (pin wording, a deployment claim). Instrument: claim 1 run twice, prefix caching on and off, reporting both. Kill test: none needed if both numbers are reported; the claim fails if only the cold-prompt number is reported as deployment cost.
7. The checker's compliance rate is meaningful. Instrument: a hand-labelled sample of A0 and A1 outputs scored against the 53 rules. Kill test: checker-vs-human agreement too low to rank arms (arm order flips on the labelled sample).

## Direction
The project wins as a Measurement paper: the first measurement of the reasoning-token cost of a fixed controlled vocabulary on current open reasoning models, an axis docs/lit-review.md found empty. The pattern's bar is "the sample is representative and the systems are current": the models are current, the sample and decoding are not. Run claim 1 first, at vendor thinking sampling with an untruncated budget and k samples, on Qwen3.8-27B on one MI350X; it alone decides H1 against H0 on cost, and claim 2 rides on the same samples. Stop three things: greedy decoding with a 1024-token cap (it truncates and destabilizes thinking output, so token counts measure the cap), GSM8K and MMLU as the accuracy instrument (saturated and noisy), and vLLM bring-up on the MI100 (outside vLLM's GPU list; use it for hf-backend plumbing only). Hold the watermark axis until claim 1 returns.

## Sound
- Model currency checked against the HF API: both picks are the newest dense checkpoints in their lines and fit one MI350X in BF16.
- The pin's confound list (A2 silent repair, degeneracy as a third outcome, checker validation) checked against the arms: complete for claims 1-3.
- The A0/A2/A1 arm order checked: A2 first gives the clean tax number, as the pin states.

## Ask
Is the target claim about the mechanism in open reasoning models, or about the cost a deployer pays on frontier closed models (docs/intervention-pin.md open decision 3 still names "one frontier reasoning model")? The second needs API spend outside this envelope.
