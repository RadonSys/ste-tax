# Experiment plan: models, hardware, protocol

Companion to docs/design.md and docs/intervention-pin.md. This file pins
the base models and the protocol. Harness: eval/README.md. Procedure on
the nodes: docs/runbook.md. Reconciled 2026-10-08 with
docs/fact-check-hardware.md, docs/advisor-review.md,
docs/lit-review-reasoning-cost.md, and docs/checker-validation.md.
Closest prior work and the gap this plan targets (tokens, reasoning,
latency, STE Issue 9, intervention comparison): docs/lit-review-cnl.md,
summarized in docs/design.md.

## Models

Model currency is a validity requirement, not a preference: a result on
superseded checkpoints invites the objection that current models behave
differently. Picks below are the newest published weights in scope as of
2026-10-08, verified against the vendors' Hugging Face listings.

Primary pair, same lineage on purpose:

- **Qwen/Qwen3.8-27B** (Aug 2026). Current Qwen generation. 27B-class
  dense model on the Qwen3.5 architecture (hybrid linear and full
  attention), published as a vision-language checkpoint; the harness
  serves it text-only. Checkpoint: 55.6 GB BF16 including the vision
  tower. Apache-2.0.
- **Qwen/Qwen3.5-9B** (Feb 2026). Same architecture family, same
  248,320-token vocabulary. The 3.8 line publishes no text model under
  27B, so the smaller rung comes from the 3.5 line. Checkpoint: 19.3 GB
  BF16. Apache-2.0.

Why this pair:

- The scaling question (does the tax grow or shrink with model size?)
  needs one tokenizer and one thinking switch at both sizes. This pair
  gives that at a roughly 3x size ratio, current generation at the
  frontier rung.
- Thinking is on by default and separable: a <think> segment precedes
  the final response, the harness counts it from token ids, and
  `enable_thinking` switches it per request, so a thinking-off control
  costs no extra model. Qwen3.8 also exposes `reasoning_effort`.
- vLLM lists the architecture (Qwen3_5ForConditionalGeneration) as
  supported, and the Qwen3.8-27B card links an official vLLM recipe
  (`min_vllm_version` 0.17.0). That recipe verifies no AMD GPU. No AMD
  validation of Qwen3.8-27B exists; the MI350X smoke test is the first
  (docs/dcs-amd-hardware.md, section 4).

Cross-family option, not in the primary pair:

- **GLM-4.7-Flash** (Jan 2026; 30B total, 3B active MoE) is the newest
  GLM that fits the scope. The GLM-5 line (Feb-Aug 2026) publishes
  nothing small: GLM-5.3-Flash's checkpoint is 328 GB, the 5.3 flagship
  756 GB. GLM-4.7-Flash posts the highest vendor card scores of any
  in-scope GLM (AIME 25 = 91.6; card claims). Its costs: MoE paths on
  gfx950 are the least settled part of the stack, its card warned
  vLLM support was main-branch-only at release, and no MI350X
  validation was found. Status: optional third model for family
  robustness, gated on a gfx950 smoke test under the image's vLLM.

Excluded:

- **DeepSeek.** No current in-scope weights exist. The V4 line
  (Apr-Sep 2026) starts at 284B total. The only sub-40B DeepSeek
  reasoning checkpoints are the Jan 2025 R1 distills on a Qwen2.5
  base; using them would create the outdated-model objection this
  selection exists to remove.
- **Qwen3 (Apr 2025) and older Qwen lines.** Superseded by 3.5/3.6/3.8.
  An earlier draft of this plan pinned Qwen3-32B and Qwen3-14B; the
  sweep to current generations replaced them.

## Hardware fit (DCS AMD donation)

Hardware and stack facts: docs/dcs-amd-hardware.md. Procedure:
docs/runbook.md. Summary:

- MI350X: 288 GB HBM3E per GPU, 8 per node, gfx950. Stack: AMD's ROCm
  vLLM Docker image. ROCm 10.1.0 (2026-10-05) ships vLLM 0.29.0;
  upstream vLLM is 0.31.0. Expect vLLM 0.29 or newer and record the
  exact version. The Qwen3.8-27B checkpoint is 55.6 GB in BF16: one
  GPU, large KV headroom. No tensor parallelism, no quantization.
- MI100 node: 32 GB per GPU. gfx908 is outside vLLM's and AITER's GPU
  lists. It runs the `hf` backend for plumbing only, never a reported
  number. (Qwen3.5-9B in BF16 leaves about 9.5 GB for KV there.)
- Access status: allocation not yet in hand. Path is PI sponsorship
  plus account provisioning via the AMD lab manager. Questions for the
  lab manager: docs/runbook.md, section 0.

## Protocol

- Tasks (docs/tasks.md):
  - Cost axis (claim 1): `eval/tasks/gsm8k_full.jsonl`, all 1319 GSM8K
    test items. Power: sd of log reasoning tokens about 0.95 (arXiv
    2511.04108, Table 5, lognormal conversion by the review), n = 1108
    for a 10% effect at alpha 0.05/4.
  - Accuracy (claim 3): `eval/tasks/math500.jsonl`, 200 numeric-answer
    MATH-500 items. GSM8K is saturated. At n = 200, power for a
    5-point drop is 0.36 per sample; more items need the 318-item
    numeric pool or symbolic answer checking.
  - `eval/tasks/nq_open.jsonl` (400) as is; `eval/tasks/writing.jsonl`
    (26) for compliance and cost; `eval/tasks.jsonl` (22) is the
    plumbing set, never pooled with the benchmarks.
- Arms in pin order: A0 free-form, A2 post-hoc rewrite, A1 prompt
  instruction with the approved list attached.
- Decoding (default `--decoding thinking`): the Qwen3.8-27B card's
  thinking-mode sampling, temperature 1.0, top-p 0.95, top-k 20
  (huggingface.co/Qwen/Qwen3.8-27B, Best Practices, retrieved
  2026-10-08); `--max-new-tokens` 16384; k = 3 samples per task and
  arm, sample s seeded with seed + s. Both sizes run the same settings:
  the Qwen3.5-9B card's general thinking set adds presence_penalty 1.5,
  not used, so the size contrast has one sampler. `--decoding greedy`
  (temperature 0, 1024 new tokens, one sample) is the plumbing setting:
  the cap truncates thinking output, so its token counts measure the
  cap. Never a reported number.
- Metrics per task, arm, and sample: accuracy on the final text,
  reasoning tokens (think segment), generated tokens, latency, naive
  compliance, checker raw `ok`, checker `gate_ok`, degeneracy and
  truncation flags. Summary per arm: mean±sd over the k samples, then
  the tax as A1-A0 and A2-A0 deltas.
- Compliance: report `gate_ok` (docs/checker-validation.md, gate row
  4) with its 4.4% STE false-reject floor and 89.1% headword recall.
  Absolute rates from raw `ok` are invalid: it rejects 44.8% of the
  spec's own STE examples. Arm comparisons under one checker and one
  allow list stand.
- Prefix caching: off by default (cold-prompt cost). Claim 6 (advisor
  review): run the cost set once more with `--prefix-caching` and
  report both.
- Watermark axis: on hold until claim 1 returns (docs/advisor-review.md,
  Direction). docs/watermark.md recommends EWD detection and a
  unique-pair z beside the raw z; referenced here, not implemented.
  The existing `run --watermark` path (hf backend, KGW, gamma 0.25,
  delta 2.0) stays as built.

## Run commands

Local plumbing test (no model):

    uv run python -m eval run --backend mock --decoding greedy

Local real-model smoke (CPU, fixture model only, not an experiment
model):

    uv run --extra hf python -m eval run --backend hf \
      --model Qwen/Qwen3.5-0.8B --limit 2 --decoding greedy --max-new-tokens 192

Cluster: docs/runbook.md, sections 4 and 5. Results land in
`eval/results/<run-id>/`, one record per task, sample, and arm.

## Known limits of the preliminary code

- Sequential generation (batch 1). Latency is per-task and honest;
  throughput is not optimized.
- A1 attaches the approved id list (879 entries), not the full
  dictionary text. The pin says "with the dictionary attached"; the id
  list is the compact form. Flagged as a design choice to revisit.
- Compliance has three numbers: the naive vocabulary rate
  (scripts/validate.py), the asd-ste100 checker's raw `ok`, and the
  validated `gate_ok`. None examines meaning (rule 1.3). The gate's H
  list is in-sample (docs/checker-validation.md, Limits).
- Watermark bias is implemented for the hf backend only. vLLM raises
  NotImplementedError for the watermark processor.
