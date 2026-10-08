# DCS AMD AI hardware: what is there, what runs on it

Reconciled 2026-10-08 with docs/fact-check-hardware.md: its eight
corrections (c-10, c-18, c-27, c-29, c-31, c-38, c-46, c-47) applied,
and its four decision-relevant findings folded into section 4.

Purpose: the hardware and stack facts this repo's experiment rests on,
for the University of Toronto DCS AMD systems. The procedure from node
login to results is docs/runbook.md. Facts come from two sources,
labeled inline: [invite] is the DCS announcement of the AMD session
(October 2026); [ext] is external, verified 2026-10-06/07 against AMD,
ROCm, and vLLM sources (full brief: amd-mi350x-uoft-brief.md in the
operator's files) and fact-checked 2026-10-08
(docs/fact-check-hardware.md, URLs there and in section 7). Anything
not yet confirmed on site is [unknown].

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
manager. This repo's experiment has no allocation yet. Open questions
for the lab manager: docs/runbook.md, section 0. Design assumption:
single-node jobs only; nothing in the eval needs multi-node.

## 2. MI350X nodes (2x) [ext]

Per GPU:

- Architecture: CDNA 4 (gfx950), TSMC 3nm compute chiplets, 256 compute
  units, 1024 matrix cores. Launched June 2025.
- Memory: **288 GB HBM3E per GPU, 8 TB/s peak bandwidth**, 256 MB
  Infinity Cache, full-chip ECC.
- Compute, dense peak: BF16/FP16 2.3 PFLOPS, FP8 4.6 PFLOPS, FP4 9.2
  PFLOPS. (Sparse figures, where AMD lists them, are 2x; MX formats
  have none.)
- Power: 1000 W per module, air-cooled.
- Scale-up: 7 Infinity Fabric links per GPU, 153.6 GB/s bidirectional
  each, about 1,075 GB/s aggregate per GPU, all-to-all 8-GPU mesh
  inside the node. Scale-up stops at 8 GPUs; there is no rack-scale
  fabric.

Per node: 8 GPUs, **2.3 TB HBM3E**, about 18.4 PFLOPS BF16 dense, PCIe
Gen 5 x16 host attach per GPU. Host CPUs: [unknown] (AMD's platform
datasheet names none; the brief's "two 5th Gen EPYC (Turin)" is
unverified, fact-check c-15). Record `lscpu` on site.

Context: on dense compute one MI350X is roughly at NVIDIA B200 parity
(BF16 2.3 vs 2.25 PFLOPS) and far ahead of H100/H200. Its edge is
memory per GPU: 1.6x B200 (180 GB), 2x H200 (141 GB), 3.6x H100
(80 GB). NVIDIA's B300 lists 288 GB, so the memory edge does not hold
against B300. Latency results from this hardware are not a toy-GPU
artifact.

## 3. MI100 node (1x) [ext]

Per GPU: CDNA 1 (gfx908), launched 2020, 120 compute units, **32 GB
HBM2 at about 1.23 TB/s**, FP16 matrix about 185 TFLOPS, 300 W.

ROCm 7.14.0 and 10.1.0 list gfx908 (AMD release notes, 2026-10-08).
vLLM's ROCm GPU list and AITER's supported-hardware list do not. Role
for this repo: the `hf` backend for plumbing and tooling tests only.
No vLLM bring-up there, and never a reported number. It is about 12x
slower per GPU than MI350X on dense FP16. `python3 -m eval preflight`
flags gfx908 under `--backend vllm`.

## 4. Software stack [ext]

- ROCm releases, as of 2026-10-08: **10.1.0 (2026-10-05)** is the
  newest; 10.0.0 (2026-08-26), 7.14.1 (2026-09-02), and 7.14.0
  (2026-07-15) came before. The version jump from 7.14 to 10.0 follows
  the TheRock transition. MI350X support began at ROCm 7.0.
- ROCm 10.1.0 ships PyTorch 2.14.0, JAX 0.11.1, **vLLM 0.29.0**, and
  SGLang 0.5.18 (AMD's 10.1.0 notes, one organization). ROCm 7.14.0
  shipped PyTorch 2.12.0, JAX 0.10.0, vLLM 0.23.0 (release notes:
  "inference-ready vLLM images and packages"), and SGLang 0.5.13.
  Upstream vLLM is at 0.31.0 (2026-10-05; docs/advisor-review.md).
- Pre-flight expectation: **vLLM 0.29 or newer; record the exact
  version**. `preflight` fails below 0.29. [unknown] Which ROCm and
  vLLM the DCS nodes run.
- The path on a node is **AMD's ROCm vLLM Docker image**, not pip
  wheels. vLLM's `rocm700` release wheels stop at 0.18.0 and
  `rocm721` is nightly only, so no prebuilt release wheel matches a
  current stack (fact-check c-33). Plain pip installs also land short
  of claimed throughput; torchvision pinning and the FlashAttention
  Triton AMD backend flag are manual.
- vLLM's GPU install docs list MI350 (gfx950). AMD's AITER kernel
  library lists gfx950 and its vLLM integration as production
  (attention, paged attention, fused MoE, GEMM, RMSNorm, RoPE, KV
  operations). Dense decoder models sit on the most exercised path.
  The newest MoE paths on gfx950 are less settled; the vLLM recipes
  repo pins a nightly ROCm image for one gfx950 MoE path.
- **No AMD validation of Qwen3.8-27B exists.** The vLLM recipe for it
  verifies no AMD GPU and says "naming it here would imply a tested
  AMD path that does not exist"; non-NVIDIA hardware falls back to
  the generic nightly image. Its `min_vllm_version` is 0.17.0. The
  MI350X smoke run (docs/runbook.md) is the first AMD validation of
  the primary model.
- Collectives (RCCL) matter only if a job spans GPUs. This eval runs
  one GPU per model, so RCCL is out of the measurement path. RCCL
  peer-to-peer can silently fall back to host-memory bounce buffers;
  irrelevant at one GPU.
- ROCm releases land about every six weeks and can strand pinned
  stacks. The run manifest records `rocminfo`, `rocm-smi`, and package
  versions with every result.

## 5. Fit to this experiment

The eval (docs/experiment-plan.md, eval/README.md) is single-model,
batch-1, sequential inference with per-task latency. Models and weights:

| Model | BF16 checkpoint | FP8 checkpoint | Placement |
| --- | --- | --- | --- |
| Qwen3.8-27B (27B dense, incl. vision tower) | 55.6 GB | about 31 GB | 1x MI350X |
| Qwen3.5-9B (9B dense, incl. vision tower) | 19.3 GB | n/a | 1x MI350X; MI100 for hf plumbing only |
| GLM-4.7-Flash (30B MoE, optional) | about 62 GB | none from the vendor found | 1x MI350X, smoke-test first |

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
  The harness sets `max_model_len` 32,768 (prompt plus the 16,384
  new-token default); that binds long before memory does. Conclusion:
  one GPU, BF16, tensor parallelism 1. No quantization, so precision
  is not a confound.
- Qwen3.5-9B: 32 layers, 8 of them full attention, 4 KV heads, head
  dim 256: 32 KB per token. On MI350X it is trivially small. On one
  MI100 GPU (32 GB), BF16 weights (19.3 GB) leave about 9.5 GB at 0.90
  utilization, roughly 290k KV tokens. Memory fits; the serving stack
  does not (section 3).

Design consequences:

- One GPU per run means no tensor parallelism and no collectives in
  the latency path. Latency differences between arms are model and
  sampler, not fabric. Keep it so; it is what makes the tax
  measurement clean.
- Two MI350X nodes exist. Split by model, one per node. Keep one arm's
  tasks sequential on one GPU so per-task latency stays comparable
  within an arm.
- A1 attaches the approved word list (879 entries) to every prompt.
  Prompt length is a few thousand tokens; prefill cost lands in A1/A2
  latency. That is part of the measured tax, not noise. vLLM prefix
  caching is on by default in recent versions; with it on, the shared
  system prompt is paid once per process, which understates A1's
  deployed cost. Harness default: off (`enable_prefix_caching=False`),
  the cold-prompt number. Claim 6 of docs/advisor-review.md needs both
  numbers: run once more with `--prefix-caching`.
- Reasoning tokens: Qwen3.5/3.8 emit a <think> segment; vLLM offline
  returns raw token ids and the harness counts the span itself, so no
  server-side reasoning parser is required. (A server would take the
  Qwen3.8-27B card's vLLM recipe flags; the GLM parser is `glm45`.)
- Decoding: the vendor's thinking-mode sampling, k samples per task,
  sample s seeded with seed + s (eval/README.md, Config defaults).
  vLLM takes the seed per request, so one seed reproduces one sample
  on one GPU up to kernel nondeterminism in reductions. The spread
  over k samples is part of the result, not jitter to remove.

## 6. What this hardware cannot settle

- Nothing about multi-node or fabric behavior. The eval does not need
  it. (For the record: node NICs are [unknown]. AMD ships Pensando
  Pollara 400GbE UEC NICs; their pairing with the MI350X reference
  platform is unverified, fact-check c-56. Irrelevant here.)
- Fine-tuning arms. The pin defers fine-tuning on design grounds, not
  hardware grounds; the nodes could train 14B/32B fine-tunes, but that
  measures training, not the inference tax.
- Frontier closed models. No API is involved; all numbers are local
  open-weight models by design.

## 7. Sources

- DCS invitation to the AMD information and training session,
  October 5, 2026 (session facts, system composition, contact).
- docs/fact-check-hardware.md (2026-10-08): per-claim quotes, URLs,
  and access dates for every [ext] fact above.
- AMD MI350X product page: https://www.amd.com/en/products/accelerators/instinct/mi350/mi350x.html
- ROCm release history: https://rocm.docs.amd.com/en/latest/release/versions.html
- ROCm 10.1.0 release notes: https://rocm.docs.amd.com/en/latest/about/release-notes.html
- ROCm 7.14.0 release: https://github.com/ROCm/ROCm/releases/tag/rocm-7.14.0
- vLLM ROCm installation (GPU list, wheels): https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.rocm.inc.md
- AITER kernel library (supported hardware): https://github.com/ROCm/aiter/blob/main/README.md
- Full operator brief with per-claim sourcing: amd-mi350x-uoft-brief.md
  (2026-10-06, corrected 2026-10-07), held outside this repo.
