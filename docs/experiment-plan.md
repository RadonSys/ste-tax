# Experiment plan: models, hardware, protocol

Companion to docs/design.md and docs/intervention-pin.md. This file pins
the base models and the run procedure. The harness is eval/harness.py.

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
  supported, and the Qwen3.8-27B card links an official vLLM recipe.
  The architecture predates the pinned ROCm vLLM build; no new arch
  support is needed for the 3.8 checkpoint itself.

Cross-family option, not in the primary pair:

- **GLM-4.7-Flash** (Jan 2026; 30B total, 3B active MoE) is the newest
  GLM that fits the scope. The GLM-5 line (Feb-Aug 2026) publishes
  nothing small: GLM-5.3-Flash's checkpoint is 328 GB, the 5.3 flagship
  756 GB. GLM-4.7-Flash posts the highest vendor card scores of any
  in-scope GLM (AIME 25 = 91.6; card claims). Its costs: MoE paths on
  gfx950 are the least settled part of the stack, its card warned
  vLLM support was main-branch-only at release, and no MI350X
  validation was found. Status: optional third model for family
  robustness, gated on a gfx950 smoke test under the pinned vLLM.

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

Full hardware analysis, run procedure, and pre-flight checks:
docs/dcs-amd-hardware.md. Summary:

- MI350X: 288 GB HBM3E per GPU, 8 per node, gfx950, ROCm 7 with
  vLLM 0.23. The Qwen3.8-27B checkpoint is 55.6 GB in BF16: one GPU,
  large KV headroom. No tensor parallelism, no quantization; BF16
  only, so quantization is not a confound.
- MI100 node: 32 GB per GPU. Qwen3.5-9B in BF16 (19.3 GB) fits one
  GPU with about 11 GB to spare for KV. Use the MI100 node for
  bring-up and the small model; MI350X for the main runs.
- Access status: allocation not yet in hand. Path is PI sponsorship
  (faculty ask) plus account provisioning via the AMD lab manager.
  Everything below runs the day access lands.

## Protocol (preliminary)

- Tasks: eval/tasks.jsonl, 22 starter tasks. 12 math word problems and
  8 factual QA with checkable answers; 2 technical-writing prompts,
  unscored, used for compliance, cost, and the watermark runs. This set
  is a plumbing test, not a benchmark. Before any claim, expand with
  standard subsets (GSM8K, MMLU) and more writing tasks.
- Arms in pin order: A0 free-form, A2 post-hoc rewrite, A1 prompt
  instruction with the approved list attached. Temperature 0,
  max 1024 new tokens, seed 0.
- Metrics per task and arm: accuracy on the final text, reasoning
  tokens (think segment), generated tokens, latency, compliance rate
  (validate.py trie over data/lexicon.json), degeneracy flag. Summary
  prints per-arm means and the tax as A1-A0 and A2-A0 deltas.
- Watermark: eval/harness.py --watermark (hf backend). Green-list
  watermark, gamma 0.25, delta 2.0, temperature 0.7, on the writing
  tasks, A0 vs A1, z-scores at full and matched length.

## Run commands

Entry point is now `python -m eval run`, from the repo root. Current commands: eval/README.md.

Local plumbing test (no model):

    python3 eval/harness.py --backend mock

Local real-model smoke (CPU works, slow; fixture only, not an
experiment model):

    uv run --with transformers --with torch --with accelerate \
      python eval/harness.py --backend hf \
      --model Qwen/Qwen3.5-0.8B --limit 2 --max-new-tokens 192

Cluster (inside the ROCm/vLLM environment on a DCS node):

    git clone --recurse-submodules https://github.com/RadonSys/ste-tax.git
    cd ste-tax
    python eval/harness.py --backend vllm --model Qwen/Qwen3.8-27B
    python eval/harness.py --backend vllm --model Qwen/Qwen3.5-9B

Results land in eval/results/*.jsonl, one record per task and arm.

## Known limits of the preliminary code

- Sequential generation (batch 1). Latency is per-task and honest;
  throughput is not optimized.
- A1 attaches the approved id list (879 entries), not the full
  dictionary text. The pin says "with the dictionary attached"; the id
  list is the compact form. Flagged as a design choice to revisit.
- The compliance checker is the naive vocabulary check: necessary, not
  sufficient (no POS, meaning, or rule checks). See scripts/validate.py.
- Watermark bias is implemented for the hf backend only. vLLM raises
  NotImplementedError for the watermark processor.
