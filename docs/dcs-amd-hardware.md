# DCS AMD AI hardware: what is there, what runs on it, how the eval uses it

Purpose: everything a coding agent needs to design and run this repo's
experiment on the University of Toronto DCS AMD systems, without internet
access. Facts come from two sources, labeled inline: [invite] is the DCS
announcement of the AMD session (October 2026); [ext] is external,
verified 2026-10-06/07 against AMD, ROCm, and vLLM sources (full brief:
~/workspace/your_files/amd-mi350x-uoft-brief.md in the operator's files,
URLs in section 8). Anything not yet confirmed on site is [unknown].

## 1. The systems [invite]

- AMD donated three systems to UofT CS: **two 8-way MI350X systems and
  one 8-way MI100 system**.
- System configuration is complete. The systems are presented as ready
  for research use by faculty, students, and staff.
- AMD and DCS ran an information and training session on Monday,
  October 5, 2026, 1:00-4:00 p.m., Room 9199, 9th floor, 700 University
  Ave. General session 1:00-2:30 p.m. (system introduction, ROCm/HIP
  overview, guidance on research use). After it: project-specific
  training for current AMD-affiliated PIs and research groups, and
  others interested in project opportunities with AMD.
- Contact for attendance and questions: Wendy Wu, AMD Lab Manager,
  wendymj.wu@utoronto.ca.
- The invite names the MI350X as AMD's flagship enterprise AI
  accelerator, 4th Generation CDNA architecture, 288 GB HBM3E per GPU.

Access model, as far as it is known: no self-serve signup is published.
The session structure (general audience, then PI-specific training)
implies the path is PI sponsorship plus provisioning by the AMD lab
manager. Open items to confirm with Wendy Wu before planning runs:
account provisioning process for students, scheduler and GPU-hour
policy, and installed software versions. This repo's experiment has no
allocation yet. Design assumption: single-node jobs only; nothing in
the eval needs multi-node.

## 2. MI350X nodes (2x) [ext]

Per GPU:

- Architecture: CDNA 4 (gfx950), TSMC 3nm compute chiplets, 256 compute
  units, 1024 matrix cores. Launched June 2025.
- Memory: **288 GB HBM3E per GPU, 8 TB/s peak bandwidth**, 256 MB
  Infinity Cache, full-chip ECC.
- Compute, dense peak: BF16/FP16 2.3 PFLOPS, FP8 4.6 PFLOPS, FP4 9.2
  PFLOPS. (Sparse figures are 2x.)
- Power: 1000 W per module, air-cooled.
- Scale-up: 7 Infinity Fabric links per GPU, 153.6 GB/s bidirectional
  each, about 1,075 GB/s aggregate per GPU, all-to-all 8-GPU mesh
  inside the node. Scale-up stops at 8 GPUs; there is no rack-scale
  fabric.

Per node: 8 GPUs, **2.3 TB HBM3E**, about 18.4 PFLOPS BF16 dense, two
5th Gen EPYC (Turin) host CPUs, PCIe Gen 5 x16 host attach per GPU.

Context: on dense compute one MI350X is roughly at NVIDIA B200 parity
(BF16 2.3 vs 2.25 PFLOPS) and far ahead of H100/H200. Its decisive edge
is memory per GPU: 1.5x B200 (192 GB), 2x H200 (141 GB), 3.6x H100
(80 GB). Latency results from this hardware are not a toy-GPU artifact.

## 3. MI100 node (1x) [ext]

Per GPU: CDNA 1 (gfx908), launched 2020, 120 compute units, **32 GB
HBM2 at about 1.23 TB/s**, FP16 matrix about 185 TFLOPS, 300 W.

Role for this repo: bring-up, CI, and the small model. It is about 12x
slower per GPU than MI350X on dense FP16 and must never carry a
performance claim. [unknown] Whether the installed ROCm 7.x still
supports gfx908; ROCm's supported-GPU list is explicit per release.
Verify on site (section 6, step 0) before scheduling any MI100 run.
Fallback if unsupported: pin the node to its older stack, or use it
only for CPU-side tooling tests.

## 4. Software stack [ext]

- ROCm 7.x is the toolchain. MI350X support began at ROCm 7.0. The
  newest production release verified externally is ROCm 7.14.0, which
  ships PyTorch 2.12.0, JAX 0.10.0, **vLLM 0.23.0 (described as
  deployment-ready)**, SGLang 0.5.13, on TheRock modular builds.
  [unknown] Which ROCm version is installed on the DCS nodes.
- PyTorch ships official ROCm wheels; MI350X target is gfx950.
- vLLM's GPU install docs list MI350 (gfx950) as supported, with
  rocm700/rocm721 wheel variants. AMD's AITER kernel library lists
  gfx950 as supported and its vLLM integration as production, covering
  attention, paged attention, fused MoE, GEMM, RMSNorm, RoPE and KV
  operations. Dense decoder models (this repo's picks) sit on the most
  exercised path. The newest MoE paths on gfx950 are less settled; the
  vLLM recipes repo pins a nightly ROCm image for one gfx950 MoE path.
- Collectives (RCCL) matter only if a job spans GPUs. This eval runs
  one GPU per model, so RCCL is out of the measurement path.

Rough edges, all [ext] reported:

- Use AMD's documented Docker images. Plain pip installs land well
  short of claimed throughput; details like torchvision pinning and the
  FlashAttention Triton AMD backend flag are manual.
- RCCL peer-to-peer can silently fall back to host-memory bounce
  buffers. Irrelevant at one GPU; relevant if anyone scales out.
- ROCm releases land about every six weeks and can strand pinned
  stacks. Record `rocminfo` and `rocm-smi` output with every result.

## 5. Fit to this experiment

The eval (docs/experiment-plan.md, eval/harness.py) is single-model,
batch-1, sequential inference with per-task latency. Models and weights:

| Model | BF16 checkpoint | FP8 checkpoint | Placement |
| --- | --- | --- | --- |
| Qwen3.8-27B (27B dense, incl. vision tower) | 55.6 GB | about 28 GB | 1x MI350X |
| Qwen3.5-9B (9B dense, incl. vision tower) | 19.3 GB | n/a | 1x MI350X, or 1x MI100 |
| GLM-4.7-Flash (30B MoE, optional) | about 62 GB | about 31 GB | 1x MI350X, smoke-test first |

Both Qwen picks are the vendors' current generations (3.8: Aug 2026;
3.5: Feb 2026) and share one tokenizer. GLM-4.7-Flash (Jan 2026) is the
newest GLM in scope: the GLM-5 line publishes nothing under a 328 GB
checkpoint. Model rationale: docs/experiment-plan.md.

KV cache math (BF16, per token = full-attention layers x KV heads x
head dim x 2 for K and V x 2 bytes). Both Qwen models use hybrid
attention: only every 4th layer is full attention and caches KV; the
linear-attention layers carry a fixed-size state instead.

- Qwen3.8-27B: 64 layers, 16 of them full attention, 4 KV heads, head
  dim 256: 64 KB per token. On one MI350X with vLLM at 0.90 GPU memory
  utilization, the budget is about 259 GB; after 55.6 GB of weights
  and runtime, roughly 195 GB remains, on the order of 3M KV tokens.
  The native context (262,144) and the harness cap of 16,384 tokens
  bind long before memory does. Conclusion: one GPU, BF16, tensor
  parallelism 1. No quantization, so precision is not a confound.
- Qwen3.5-9B: 32 layers, 8 of them full attention, 4 KV heads, head
  dim 256: 32 KB per token. On MI350X it is trivially small. On one
  MI100 GPU (32 GB), BF16 weights (19.3 GB) leave about 11 GB, roughly
  340k KV tokens: comfortable in BF16, no FP8 needed. MI100 plan: 9B
  for bring-up and functional runs; all reported numbers from MI350X
  in BF16.

Design consequences:

- One GPU per run means no tensor parallelism and no collectives in
  the latency path. Latency differences between arms are model and
  sampler, not fabric. Do not "optimize" this away; it is what makes
  the tax measurement clean.
- Two MI350X nodes exist. Run the two models in parallel, one per
  node, or parallelize arms. Keep one arm's tasks sequential on one
  GPU so per-task latency stays comparable within an arm.
- A1 attaches the approved word list (879 entries) to every prompt.
  Prompt length is a few thousand tokens; prefill cost lands in A1/A2
  latency. That is part of the measured tax, not noise. vLLM prefix
  caching is on by default in recent versions; if it is enabled, the
  shared system prompt is paid once per process, which understates
  A1's deployed cost. The harness does sequential single calls, so
  decide explicitly: leave prefix caching on and say so in results,
  or disable it (`--no-enable-prefix-caching` in server terms; the
  offline LLM takes `enable_prefix_caching=False`) for the
  cold-prompt number. Preliminary runs: disable it.
- Reasoning tokens: Qwen3.5/3.8 emit a <think> segment; vLLM offline
  returns raw token ids and the harness counts the span itself, so no
  server-side reasoning parser is required. (If a server is used
  instead, the Qwen3.8-27B card's vLLM recipe names the serve flags;
  the GLM parser is `glm45`.)
- Determinism: temperature 0 and fixed seed in the harness config.
  vLLM greedy decoding is deterministic per prompt on one GPU, up to
  kernel nondeterminism in reductions; treat small run-to-run latency
  jitter as expected, token outputs should match exactly.

## 6. Run procedure on a DCS node

Step 0, pre-flight (record all output with the results):

    rocminfo | grep -A2 gfx        # expect gfx950 on MI350X nodes
    rocm-smi                        # 8 GPUs, 288 GB each on MI350X
    python3 -c "import torch; print(torch.__version__, torch.cuda.is_available())"
    python3 -c "import vllm; print(vllm.__version__)"   # expect 0.23.x

On the MI100 node, step 0 decides its role: if torch does not see
gfx908, stop and use the node only for tooling tests.

Step 1, stage weights offline. Cluster internet access is [unknown].
Do not design for live downloads. Either confirm egress on site, or
stage the model directories on a connected machine and copy them to
cluster storage:

    huggingface-cli download Qwen/Qwen3.8-27B
    huggingface-cli download Qwen/Qwen3.5-9B
    export HF_HOME=<cluster storage>/hf   # or pass local paths to --model

The harness accepts a local directory as --model for both backends.

Step 2, smoke (5 minutes, proves the stack end to end):

    git clone --recurse-submodules https://github.com/RadonSys/ste-tax.git
    cd ste-tax
    python3 eval/harness.py --backend vllm --model Qwen/Qwen3.5-9B --limit 3

Expect three tasks across three arms, a summary block, and a results
file under eval/results/. If this fails, the failure is environmental
(image, ROCm, weights), not the harness: the same code runs on the
mock and hf backends elsewhere.

Step 3, full preliminary runs:

    python3 eval/harness.py --backend vllm --model Qwen/Qwen3.8-27B
    python3 eval/harness.py --backend vllm --model Qwen/Qwen3.5-9B

One process per GPU. For parallel arms across the two MI350X nodes,
split by model (cleaner than splitting arms: one model's arms share a
node's thermal state).

Step 4, GLM option, only if wanted: same smoke with
`--model zai-org/GLM-4.7-Flash`. Its card warned vLLM support was
main-branch-only at release and no MI350X validation is published.
A smoke failure here blocks nothing; the Qwen pair is the experiment.

## 7. What this hardware cannot settle

- Nothing about multi-node or fabric behavior. The eval does not need
  it. (For the record: node NICs are [unknown]; AMD's reference
  platform pairs Pensando Pollara 400GbE UEC NICs. Irrelevant here.)
- Fine-tuning arms. The pin defers fine-tuning on design grounds, not
  hardware grounds; the nodes could train 14B/32B fine-tunes, but that
  measures training, not the inference tax.
- Frontier closed models. No API is involved; all numbers are local
  open-weight models by design.

## 8. Sources

- DCS invitation to the AMD information and training session,
  October 5, 2026 (session facts, system composition, contact).
- AMD MI350X product page: https://www.amd.com/en/products/accelerators/instinct/mi350/mi350x.html
- ROCm 7.14.0 release: https://github.com/ROCm/ROCm/releases/tag/rocm-7.14.0
- vLLM GPU installation (gfx950 support): https://docs.vllm.ai/en/stable/getting_started/installation/gpu/
- AITER kernel library (gfx950, vLLM production): https://github.com/ROCm/aiter
- Full operator brief with per-claim sourcing: amd-mi350x-uoft-brief.md
  (2026-10-06, corrected 2026-10-07), held outside this repo.
