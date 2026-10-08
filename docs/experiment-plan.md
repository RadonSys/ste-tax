# Experiment plan: models, hardware, protocol

Companion to docs/design.md and docs/intervention-pin.md. This file pins
the base models and the run procedure. The harness is eval/harness.py.

## Models

Primary pair, same family on purpose:

- **Qwen/Qwen3-32B.** 32.8B dense. BF16 weights about 65.6 GB.
- **Qwen/Qwen3-14B.** 14.8B dense. BF16 weights about 29.6 GB.

Why this pair:

- The scaling question (does the tax grow or shrink with model size?)
  needs one tokenizer, one chat template, one thinking switch at both
  sizes. Qwen3 gives that. Token counts, the primary cost axis, stay
  comparable across the pair.
- Both have hybrid thinking: a separable <think> segment that the harness
  counts directly from token ids. Thinking on/off is a template switch,
  so a thinking-off control costs no extra model.
- Dense Qwen3 is the most exercised architecture on the ROCm/AITER
  stack. vLLM lists gfx950 (MI350) as supported; AITER lists vLLM
  integration on gfx950 as production.

Rejected for the primary pair:

- **GLM-4.7-Flash** (30B total, 3B active MoE) posts the highest vendor
  card scores in scope (AIME 25 = 91.6). Three problems. No sub-30B GLM
  sibling exists, so the size pair would be cross-family and token
  counts stop being comparable. Its card states vLLM support was
  main-branch-only at release, and no MI350X validation was found; MoE
  paths on gfx950 are the least settled part of the stack. Card scores
  are vendor claims. Status: optional third model for family
  robustness, gated on a gfx950 smoke test under the pinned vLLM.
- **DeepSeek.** The only in-scope checkpoint is
  DeepSeek-R1-Distill-Qwen-32B (Jan 2025, Qwen2.5 base): always-on
  chain-of-thought with no thinking-off arm, and a different tokenizer
  from the Qwen3 pair. The V4 line is 284B and up, out of scope.

## Hardware fit (DCS AMD donation)

- MI350X: 288 GB HBM3E per GPU, 8 per node, gfx950, ROCm 7 with
  vLLM 0.23. Qwen3-32B in BF16 uses about 66 GB: one GPU, large KV
  headroom. No tensor parallelism, no quantization; BF16 only, so
  quantization is not a confound.
- MI100 node: 32 GB per GPU. Qwen3-14B in BF16 (about 30 GB) fits one
  GPU with small KV headroom, or the 32B fits across the node at TP=8.
  Use the MI100 node for bring-up and the small model; MI350X for the
  main runs.
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

Local plumbing test (no model):

    python3 eval/harness.py --backend mock

Local real-model smoke (CPU works, slow):

    uv run --with transformers --with torch --with accelerate \
      python eval/harness.py --backend hf \
      --model Qwen/Qwen3-0.6B --limit 2 --max-new-tokens 192

Cluster (inside the ROCm/vLLM environment on a DCS node):

    git clone --recurse-submodules https://github.com/RadonSys/ste-tax.git
    cd ste-tax
    python eval/harness.py --backend vllm --model Qwen/Qwen3-32B
    python eval/harness.py --backend vllm --model Qwen/Qwen3-14B

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
