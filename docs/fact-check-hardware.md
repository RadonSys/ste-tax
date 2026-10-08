# Fact-check: DCS AMD hardware brief

Skill: `/fact-check` (SKILLs library), full workflow to Step 3. No edit made: Step 4 approval belongs to the operator, and the files belong to the reconcile wave. Corrections are old-span and new-span pairs.

Scope: the `[ext]` claims of docs/dcs-amd-hardware.md and the checkpoint sizes and dates in docs/experiment-plan.md, Models section. `[invite]` claims are out of scope (no public source).

## Fact-Check Report

Checked 56 claims from docs/dcs-amd-hardware.md and docs/experiment-plan.md (claim-time: 2026-10-08, git log).
Branch: sequential (no delegation; brief forbids subagents); approx cost: NA.
Verdicts: supported 45, contradicted 4, outdated 0, conflicting 0, missing-context 4, insufficient-evidence 3, unverifiable 0.

### Decision-relevant findings

1. ROCm 7.14.0 is not the newest release. ROCm 10.0.0 (2026-08-26) and 10.1.0 (2026-10-05) predate the brief. 10.1.0 ships vLLM 0.29.0 (AMD notes). The pre-flight line `expect 0.23.x` can fail on a current node image. (c-29)
2. The MI100 is a ROCm target (gfx908 listed through 10.1.0) but not a vLLM or AITER target. Plan the MI100 for the hf backend or tooling only; do not plan vLLM runs there. (c-27, c-47)
3. The vLLM Qwen3.8-27B recipe verifies no AMD GPU. Its own text: "naming it here would imply a tested AMD path that does not exist". The MI350X smoke test is the first AMD validation of the primary model. (c-35, c-43 notes)
4. No prebuilt vLLM release wheel matches ROCm 7.x plus vLLM 0.23: `rocm700` wheels stop at 0.18.0, `rocm721` is nightly only. Use the AMD Docker image. (c-33)

### Corrections proposed

#### c-18 (spec, confidence high) docs/dcs-amd-hardware.md:58
Document says:
> 1.5x B200 (192 GB)
Evidence:
- ""NVIDIA B200 SXM" - "Memory per GPU: 180GB HBM3e"" (NVIDIA (Enterprise Reference Architecture), published n/a, accessed 2026-10-08, https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory/latest/components.html)
- "Per-GPU Memory: "180 GB"" (flopper.io (independent spec database), published n/a, accessed 2026-10-08, https://flopper.io/system/nvidia-dgx-b200/spec-sheet)
- "HGX B200 Total Memory: "1.4 TB"" (NVIDIA, published n/a, accessed 2026-10-08, https://www.nvidia.com/en-us/data-center/hgx/)
Counter-evidence or caveats: 192 GB is the early-marketing physical figure; NVIDIA's current per-GPU spec is 180 GB. 288/180 = 1.6. Same table lists B300 at 288 GB, so the 'decisive edge' sentence no longer holds against B300.
Verdict: contradicted. Proposed replacement:
> 1.6x B200 (180 GB)

#### c-29 (version, confidence high) docs/dcs-amd-hardware.md:76-77
Document says:
> The
> newest production release verified externally is ROCm 7.14.0
Evidence:
- "| "10.1.0" | "October 5, 2026" | ; | "10.0.0" | "August 26, 2026" | ; | "7.14.1" | "September 2, 2026" | ; | "7.14.0" | "July 15, 2026" |" (AMD (ROCm release history), published n/a, accessed 2026-10-08, https://rocm.docs.amd.com/en/latest/release/versions.html)
- "AMD ROCm 10.1, released October 5, puts its weight on the path between storage and the GPU." (StorageReview, published n/a, accessed 2026-10-08, https://www.storagereview.com/news/amd-rocm-10-1-hipfile-fast-path-numa-memory-llvm-24)
Counter-evidence or caveats: Wrong at claim-time 2026-10-08 and at the stated verification dates: 10.0.0 and 10.1.0 predate them. Per AMD's 10.1.0 notes (one org), 10.1.0 ships PyTorch 2.14.0, JAX 0.11.1, vLLM 0.29.0, SGLang 0.5.18; ROCm 7.14.1 (2026-09-02) also exists. Note doc-version jump 7.14 -> 10.0 follows TheRock transition.
Verdict: contradicted. Proposed replacement:
> The
> newest production release, as of 2026-10-08, is ROCm 10.1.0
> (2026-10-05). The release verified externally is ROCm 7.14.0

#### c-46 (computation, confidence medium) docs/dcs-amd-hardware.md:131-133
Document says:
> BF16 weights (19.3 GB) leave about 11 GB, roughly
> 340k KV tokens
Evidence:
- "Recomputed: 32 - 19.3 = 12.7 GB raw; at the 0.90 utilization the same section uses for MI350X, 28.8 - 19.3 = 9.5 GB before runtime overhead; 9.5e9/32,768 = 290k" (this document, published n/a, accessed 2026-10-08, docs/dcs-amd-hardware.md)
Counter-evidence or caveats: Recomputation from the document's own inputs (route: computation). The 0.90 basis is the one the document applies to MI350X two lines earlier. Both figures far exceed the 16,384-token cap, so the conclusion holds.
Verdict: missing-context. Proposed replacement:
> BF16 weights (19.3 GB) leave about 9.5 GB at 0.90 utilization, roughly
> 290k KV tokens

#### c-47 (other, confidence medium) docs/dcs-amd-hardware.md:110
Document says:
> 1x MI350X, or 1x MI100
Evidence:
- "GPU: MI200s (gfx90a), MI300 (gfx942), MI350 (gfx950), Radeon RX 7900 series (gfx1100/1101), Radeon RX 9000 series (gfx1200/1201), Ryzen AI MAX / AI 300 Series (gfx1151/1150)" (vLLM project, published n/a, accessed 2026-10-08, https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.rocm.inc.md)
- "Supported Hardware: MI300X gfx942, MI325X gfx942, MI350 gfx950, MI355X gfx950, W7900 gfx1100, ... gfx1151, gfx1201" (AMD (AITER README), published n/a, accessed 2026-10-08, https://github.com/ROCm/aiter/blob/main/README.md)
Counter-evidence or caveats: Memory fits; the serving stack does not list gfx908. The harness vllm backend may fail on MI100 even where torch sees the GPU; the hf backend is the likely fallback. Two organizations (vLLM project, AMD) both omit gfx908.
Verdict: missing-context. Proposed replacement:
> 1x MI350X, or 1x MI100 if vLLM runs on gfx908 (not in vLLM's ROCm GPU list, 2026-10-08)

### Needs your judgment (conflicting / abstained)

Single-source findings. Invariant 4 forbids a proposed correction; the note gives qualifier or dictated text only.

#### c-10 (spec, confidence medium) docs/dcs-amd-hardware.md:46
Document says:
> (Sparse figures are 2x.)
Evidence:
- "MXFP4 (PFLOPS) 73.816 N/A  [8-GPU table: dense value, sparse column N/A]" (AMD (MI350X platform datasheet), published n/a, accessed 2026-10-08, https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/product-briefs/amd-instinct-mi350x-platform-brochure.pdf)
Verdict: missing-context. AMD lists no sparse figure for MXFP4 (and MX formats); 2x holds for BF16/FP16/FP8/INT8 only. One organization only, so no correction proposed; suggested qualifier: '(Sparse figures, where AMD lists them, are 2x; MX formats have none.)'

#### c-27 (other, confidence medium) docs/dcs-amd-hardware.md:68-69
Document says:
> [unknown] Whether the installed ROCm 7.x still
> supports gfx908
Evidence:
- ""Instinct MI100" | gfx908 | "CDNA" (ROCm 7.14.0 AMD hardware support table)" (AMD (ROCm 7.14.0 release notes), published 2026-07-15, accessed 2026-10-08, https://rocm.docs.amd.com/en/docs-7.14.0/about/release-notes.html)
- "MI100: Shown as "Instinct MI100" with LLVM target "gfx908" (ROCm 10.1.0 hardware table)" (AMD (ROCm 10.1.0 release notes), published 2026-10-05, accessed 2026-10-08, https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- "GPU: MI200s (gfx90a), MI300 (gfx942), MI350 (gfx950), Radeon RX 7900 series ... [no gfx908]" (vLLM project, published n/a, accessed 2026-10-08, https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.rocm.inc.md)
- "Supported Hardware: MI300X, MI325X gfx942; MI350, MI355X gfx950 ... [no gfx908]" (AMD (AITER README), published n/a, accessed 2026-10-08, https://github.com/ROCm/aiter/blob/main/README.md)
Verdict: missing-context. ROCm itself lists gfx908 through 10.1.0, so the ROCm half of the [unknown] is settled; the open risk is the serving stack: vLLM's ROCm GPU list and AITER's list omit gfx908. Both sources are AMD for the ROCm half, so no correction under Invariant 4; suggested qualifier: 'ROCm 7.14.0 and 10.1.0 list gfx908 (AMD release notes, as of 2026-10-08); vLLM's ROCm docs and AITER do not.'

#### c-31 (quotation, confidence medium) docs/dcs-amd-hardware.md:78-79
Document says:
> (described as
> deployment-ready)
Evidence:
- "Highlights include inference-ready vLLM images and packages" (AMD (ROCm GitHub release), published 2026-07-16, accessed 2026-10-08, https://github.com/ROCm/ROCm/releases/tag/rocm-7.14.0)
Verdict: contradicted. The phrase 'deployment-ready' does not occur in the release notes; their phrase is 'inference-ready vLLM images and packages'. One source by nature (the quoted document); suggested replacement: '(the release notes say "inference-ready vLLM images and packages")'.

#### c-38 (spec, confidence medium) docs/dcs-amd-hardware.md:109
Document says:
> about 28 GB
Evidence:
- "Qwen/Qwen3.8-27B-FP8: createdAt 2026-08-13; safetensors total 30.9 GB (BF16 3.08e9 + F8_E4M3 2.47e10 params)" (Hugging Face (Qwen org), published n/a, accessed 2026-10-08, https://huggingface.co/api/models/Qwen/Qwen3.8-27B-FP8)
Verdict: contradicted. Only one publisher hosts the file sizes, so no correction under Invariant 4; dictated-text option: 'about 31 GB'. Low stakes: FP8 is not used.

### Verified accurate

- c-01: MI350X architecture is CDNA 4 with LLVM target gfx950. (AMD (ROCm docs 10.1.0))
- c-02: MI350X compute chiplets are made on TSMC 3nm. (AMD (ROCm docs 10.1.0))
- c-03: MI350X has 256 compute units. (AMD (ROCm docs 10.1.0))
- c-04: MI350X has 1024 matrix cores. (AMD (MI350X platform datasheet)) Note: Per-GPU value derived from the 8-GPU platform datasheet; product page timed out on fetch.
- c-05: MI350X launched June 2025. (HotHardware)
- c-06: MI350X has 288 GB HBM3E per GPU. (AMD (MI350X platform datasheet))
- c-07: MI350X peak memory bandwidth is 8 TB/s. (AMD (MI350X platform datasheet))
- c-08: MI350X has 256 MB Infinity Cache and full-chip ECC. (AMD (MI350X platform datasheet))
- c-09: MI350X dense peak: BF16/FP16 2.3 PFLOPS, FP8 4.6 PFLOPS, FP4 9.2 PFLOPS. (AMD (ROCm docs 10.1.0)) Note: One organization (AMD); figures also match the platform datasheet totals.
- c-11: MI350X is a 1000 W air-cooled module. (AMD (MI350X platform datasheet))
- c-12: Each MI350X has 7 Infinity Fabric links at 153.6 GB/s bidirectional each. (AMD (MI350X platform datasheet))
- c-13: Aggregate scale-up bandwidth is about 1,075 GB/s per GPU (7 x 153.6). (this document)
- c-14: An 8-GPU MI350X node has 2.3 TB HBM3E and about 18.4 PFLOPS BF16 dense. (AMD (MI350X platform datasheet))
- c-16: Each MI350X attaches to the host by PCIe Gen 5 x16. (AMD (MI350X platform datasheet))
- c-17: NVIDIA B200 dense BF16 peak is 2.25 PFLOPS per GPU. (NVIDIA)
- c-19: NVIDIA H200 has 141 GB per GPU (MI350X 2x). (NVIDIA)
- c-20: NVIDIA H100 has 80 GB per GPU (MI350X 3.6x). (NVIDIA)
- c-21: MI100 is CDNA 1 (gfx908), launched 2020. (AMD (ROCm docs 10.1.0))
- c-22: MI100 has 120 compute units. (AMD (ROCm docs))
- c-23: MI100 has 32 GB HBM2 at about 1.23 TB/s. (AMD (ROCm docs))
- c-24: MI100 FP16 matrix peak is about 185 TFLOPS. (AMD (ROCm docs))
- c-25: MI100 board power is 300 W. (AMD (Instinct acceptance guide))
- c-26: MI100 is about 12x slower per GPU than MI350X on dense FP16. (this document)
- c-28: MI350X support began at ROCm 7.0. (AMD (ROCm GitHub release))
- c-30: ROCm 7.14.0 ships PyTorch 2.12.0, JAX 0.10.0, vLLM 0.23.0, and SGLang 0.5.13 on TheRock modular builds. (AMD (ROCm GitHub release))
- c-32: PyTorch ships official ROCm wheels. (PyTorch Foundation)
- c-33: vLLM's GPU install docs list MI350 (gfx950) as supported, with rocm700 and rocm721 wheel variants. (vLLM project) Note: Caveat: rocm700 wheels cover vLLM 0.14.0-0.18.0 only and rocm721 is nightly-only, so no prebuilt release wheel matches vLLM 0.23.0; the AMD Docker image is the path.
- c-34: AITER lists gfx950 as supported and its vLLM integration as production, covering attention, paged attention, fused MoE, GEMM, RMSNorm, RoPE and KV operations. (AMD (AITER README))
- c-35: The vLLM recipes repo pins a nightly ROCm image for a gfx950 MoE path. (vLLM project (recipes)) Note: Related, same repo: the Qwen3.8-27B recipe (updated 2026-10-08) verifies no AMD GPU and says 'naming it here would imply a tested AMD path that does not exist. Non-NVIDIA hardware falls back to the generic nightly image.' Its min_vllm_version is 0.17.0.
- c-36: ROCm releases land about every six weeks. (AMD (ROCm release history))
- c-37: Qwen3.8-27B BF16 checkpoint is 55.6 GB including a vision tower, Apache-2.0, published Aug 2026. (Hugging Face (Qwen org))
- c-39: Qwen3.5-9B BF16 checkpoint is 19.3 GB, Apache-2.0, published Feb 2026. (Hugging Face (Qwen org))
- c-40: Qwen3.8-27B and Qwen3.5-9B share one 248,320-token vocabulary. (Hugging Face (Qwen org))
- c-41: The Qwen3.8 line publishes no text model under 27B. (Hugging Face (Qwen org))
- c-42: Qwen3.8 exposes reasoning_effort and enable_thinking switches thinking per request. (Qwen (model card))
- c-43: vLLM lists Qwen3_5ForConditionalGeneration as supported, and the Qwen3.8-27B card links an official vLLM recipe; the architecture predates vLLM 0.23. (vLLM project) Note: The recipe verifies no AMD hardware for Qwen3.8-27B (see c-35 notes).
- c-44: Qwen3.8-27B: 64 layers, 16 full attention, 4 KV heads, head dim 256, native context 262,144; Qwen3.5-9B: 32 layers, 8 full attention, 4 KV heads, head dim 256. (Hugging Face (Qwen org))
- c-45: KV cache is 64 KB/token (27B) and 32 KB/token (9B); one MI350X at 0.90 utilization leaves about 195 GB, about 3M tokens. (this document)
- c-48: GLM-4.7-Flash is a 30B-total, 3B-active MoE, about 62 GB BF16, published Jan 2026. (Z.ai (model card))
- c-50: The GLM-5 line (Feb-Aug 2026) publishes nothing under 328 GB: GLM-5.3-Flash is 328 GB, GLM-5.3 756 GB. (Hugging Face (zai-org))
- c-51: GLM-4.7-Flash card reports AIME 25 = 91.6 and warned vLLM support was main-branch-only. (Z.ai (model card))
- c-52: The GLM reasoning parser in vLLM is glm45. (Z.ai (model card))
- c-53: vLLM disables prefix caching with --no-enable-prefix-caching (server) or enable_prefix_caching=False (offline). (vLLM project)
- c-54: DeepSeek V4 line (Apr-Sep 2026) starts at 284B total. (DeepSeek (model card))
- c-55: DeepSeek R1 distills date from Jan 2025; Qwen3 from Apr 2025. (Hugging Face) Note: Only dates checked; the 'only sub-40B DeepSeek reasoning checkpoints' universal not checked.

### Unverifiable / insufficient evidence

- c-15: The MI350X nodes carry two 5th Gen EPYC (Turin) host CPUs. (Host CPU is a server-vendor choice; the AMD platform datasheet names none and the DCS node build is not published. Mark [unknown] until rocminfo/lscpu on site.)
- c-49: A GLM-4.7-Flash FP8 checkpoint of about 31 GB exists. (No vendor FP8 checkpoint found; 31 GB looks like half of 62 GB. A third-party FP8 may exist; not searched.)
- c-56: AMD's reference platform pairs Pensando Pollara 400GbE UEC NICs. (Shipping confirmed; pairing with the MI350X reference platform not found. Doc calls it irrelevant here.)

## Corrections as old-span / new-span pairs

| Id | File:lines | Old span | New span | Source rule |
| --- | --- | --- | --- | --- |
| c-18 | docs/dcs-amd-hardware.md:58 | 1.5x B200 (192 GB) | 1.6x B200 (180 GB) | two independent sources |
| c-29 | docs/dcs-amd-hardware.md:76-77 | The  newest production release verified externally is ROCm 7.14.0 | The  newest production release, as of 2026-10-08, is ROCm 10.1.0  (2026-10-05). The release verified externally is ROCm 7.14.0 | two independent sources |
| c-46 | docs/dcs-amd-hardware.md:131-133 | BF16 weights (19.3 GB) leave about 11 GB, roughly  340k KV tokens | BF16 weights (19.3 GB) leave about 9.5 GB at 0.90 utilization, roughly  290k KV tokens | two independent sources |
| c-47 | docs/dcs-amd-hardware.md:110 | 1x MI350X, or 1x MI100 | 1x MI350X, or 1x MI100 if vLLM runs on gfx908 (not in vLLM's ROCm GPU list, 2026-10-08) | two independent sources |
| c-31 | docs/dcs-amd-hardware.md:78-79 | (described as deployment-ready) | (release notes: "inference-ready vLLM images and packages") | single source; dictated text only |
| c-38 | docs/dcs-amd-hardware.md:109 | about 28 GB | about 31 GB | single source; dictated text only |
| c-10 | docs/dcs-amd-hardware.md:46 | (Sparse figures are 2x.) | (Sparse figures, where AMD lists them, are 2x; MX formats have none.) | single source; qualifier only |
| c-27 | docs/dcs-amd-hardware.md:68-69 | [unknown] Whether the installed ROCm 7.x still supports gfx908 | ROCm 7.14.0 and 10.1.0 list gfx908 (AMD notes, 2026-10-08); vLLM and AITER do not. [unknown] Which ROCm the node runs | single source; qualifier only |

State file: factcheck-state.json in the delegate's scratch directory (not committed); this report is regenerated from it.
