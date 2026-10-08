# Watermark sub-experiment

Instrument for the design's Watermark axis (docs/design.md): does an
ASD-STE100 vocabulary constraint lower watermark detection at matched
length? Code: `eval/watermark.py`. Tests: `tests/test_watermark.py`.
Run: `eval/harness.py --watermark` (hf backend). Bracketed numbers cite
docs/lit-review.md, Included papers. `[Sn]` cite the Sources table below.

## Scheme as implemented

KGW green list [13], LeftHash form: context width h = 1, so the previous
token alone seeds the split [S5, p.4].

- Seed: SHA-256 of the UTF-8 string `f"{key}:{prev}"`.
- Green list: `random.Random(seed).sample(range(V), k)`,
  `k = max(1, floor(gamma * V))`. Python's Mersenne Twister, not numpy.
  The hash and the sampler are frozen. A change to either changes every
  green list and makes stored z-scores void. Goldens in the tests pin
  both.
- Generation: `GreenListProcessor` adds `delta` to the logits of the green
  list of each batch row's last token, at each step.
- Detection: pair i = (ids[i], ids[i+1]). Count green pairs G over T
  pairs. `z = (G - gamma*T) / sqrt(T*gamma*(1-gamma))`. T = 0 gives
  z = 0.0. The test does not need the model.
- `unique=True` counts each distinct (prev, cur) pair once. Default off,
  same count as before.
- Matched length: `truncate_matched(a, b)` cuts both id lists to the
  shorter length. Idempotent and symmetric.

Not compatible with the transformers `WatermarkingConfig` PRF: same
family and defaults, different hash. Scores compare statistically, not
token by token, with other KGW implementations.

### Cost

V = vocabulary size (151936 for Qwen3), k = gamma*V, T = pairs, D =
distinct previous tokens.

| Function | Time | Space |
| --- | --- | --- |
| `green_ids`, `green_set` | O(V); k Python-level draws, ~4 ms at V = 151936 (unmeasured estimate) | O(V) transient, O(k) result |
| `detect`, `z_score` | O(D*V + T); was O(T*V) | O(V + T) |
| `truncate_matched` | O(min(len a, len b)) | same |
| `GreenListProcessor.__call__` | B * (green list + O(k) tensor, 300 KB host to device at Qwen3 V) per step | O(k) per row |

### Laws under test

- Green list: deterministic in (key, prev, V, gamma); size within one of
  gamma*V; ids distinct and in range.
- Null: uniform random ids give mean z near 0 and sd near 1 over 300
  seeds. Exact when gamma*V is an integer (true for Qwen3: 37984).
  Otherwise the null mean of z shifts by (k/V - gamma) * sqrt(T) /
  sqrt(gamma(1-gamma)), under 0.01 at T = 1024 for any V > 10^4.
- All-green sequence: z = sqrt(T) * sqrt((1-gamma)/gamma) exactly, so z
  doubles when T grows 4 times.
- Grouped detector equals the naive per-pair oracle.
- Truncation: idempotent, symmetric, equal-length prefixes.
- Processor: biases exactly the green ids of each row by delta. Tested
  with a numpy stand-in for torch.

Defects found on the old code, now fixed and pinned: one-token input
returned T = 1 with no pair scored; gamma 0 or 1 raised
ZeroDivisionError (now ValueError at `Scheme`); the processor biased batch
row 0 only.

## Parameters and why

| Parameter | Value | Why |
| --- | --- | --- |
| gamma | 0.25 | Reliability study default (gamma, delta) = (0.25, 2.0), "near the pareto frontier ... extremely detectable, but with marginal cost to generation quality" [S5, p.5]. Same as transformers `WatermarkingConfig` defaults [S4]. |
| delta | 2.0 | Same source as gamma. |
| context width | 1 (LeftHash) | Original KGW experiments use h = 1 [S5, p.4]. Weakest against green-list discovery [10], irrelevant here: no attacker. |
| temperature | 0.7 | Reliability study samples at 0.7 for all runs [S5, p.5]. |
| key | 42 (harness default) | Any fixed value. Module default 0. Record it with the results. |
| length | `--wm-tokens` new tokens, z at full and matched length | Detection power grows with length [13, 16]; matched length removes the length confound between A0 and A1. |

Known gaps in the harness path (harness file, not owned here): the
detector scores all generated ids, think segment and special tokens
included; `split_reasoning` output is not used. Whether HF applies the
custom processor before or after the temperature warper sets the
effective delta (2.0 or 2.0/0.7); not verified here, check on the
installed transformers before the run.

## Is KGW alone the right instrument?

Question put to `/ponder` (lite, one round, 11 searches): which
detection-side baselines do 2025 to 2026 watermark papers report beside
KGW, and would a reviewer ask for one?

### Answer

Current papers report a stable baseline set beside KGW: Unigram, EXP and
EXP-Edit, SynthID-Text, and the low-entropy pair SWEET and EWD, often
with SIR, DiPmark, and Unbiased [S1, S2, S3]. MarkLLM implements all of
them behind one interface [S1], and transformers ships both KGW and
SynthID-Text [S4]. EWD (lit review [6]) and SWEET are the low-entropy
methods; both need the model to compute entropy at detection [S1, S2].
Counting repeated n-grams once fixes the calibration of the KGW z-test:
uncorrected p-values claim a lower FPR than measured [S5, p.19];
transformers exposes the fix as `ignore_repeated_ngrams` [S6].

Decision [~]: KGW alone supports only "constrained vocabulary weakens KGW
detection". The design's claim names entropy as the mechanism, so a
reviewer will ask two things. First, does an entropy-aware detector
recover the signal? Answer with EWD [6]: same generations, detection
reweighted, one scoring forward pass, no new generation. Second, is the
effect specific to logit-bias schemes? Answer with SynthID-Text if
budget allows: in the 2025 baseline sets found [S2, S3] and in transformers [S4], but
its Bayesian detector needs training [S6]; use its mean score [S1]. STE text
repeats bigrams, which inflates raw z under the null and under the
watermark alike, so report z both raw and with `unique=True`, and
calibrate the null on unwatermarked A0 and A1 outputs, not on the
binomial alone.

Order of work: (1) repeat-corrected z, done in code; (2) empirical null
on unwatermarked outputs; (3) EWD detection; (4) SynthID-Text.

### Rival

- KGW alone suffices: the claim names green-list detection, and LeftHash
  h = 1 with (0.25, 2.0) is still the transformers default [S4]. True
  for the narrow claim; the design generalizes to "watermark detection".
- The effect is KGW-specific: sampling-based schemes embed signal
  differently. Not tested; answered only by a second scheme.
- The effect is an artifact of the uncorrected z-test: repeated bigrams
  in STE text distort z [S5, p.19]. Answered by the `unique=True` arm.

### Sources

| Marker | Class | Source |
| --- | --- | --- |
| S1 | attested | THU-BPM/MarkLLM README, https://github.com/THU-BPM/MarkLLM |
| S2 | measured | Li et al. 2025, Watermarking with Low-Entropy POS-Guided Token Partitioning and Z-Score-Driven Dynamic Bias, Findings EMNLP 2025, Table 1, https://aclanthology.org/2025.findings-emnlp.260.pdf |
| S3 | measured | Wu et al. 2025, Analyzing and Evaluating Unbiased Language Model Watermark (UWbench), https://arxiv.org/abs/2509.24048 |
| S4 | constitutive | transformers `generation/configuration_utils.py`, `WatermarkingConfig`, `SynthIDTextWatermarkingConfig`, https://github.com/huggingface/transformers/blob/main/src/transformers/generation/configuration_utils.py |
| S5 | measured | Kirchenbauer et al. 2024, On the Reliability of Watermarks for Large Language Models, ICLR 2024, https://arxiv.org/abs/2306.04634 |
| S6 | constitutive | transformers `generation/watermarking.py`, `WatermarkDetector`, `SynthIDTextWatermarkDetector`, https://github.com/huggingface/transformers/blob/main/src/transformers/generation/watermarking.py |
| S7 | attested | vLLM docs, Custom Logits Processors, https://docs.vllm.ai/en/latest/features/custom_logitsprocs/ |

Accessed 2026-10-08. S3 read at abstract level; its per-method numbers
came from a search summary and are not quoted here.

## Design question: a vLLM path

The harness watermarks on hf only; `VLLMBackend` raises
`NotImplementedError`. vLLM V1 has no per-request logits function. A
processor is a class registered at engine start, called on the whole
batch; each request opts in through `SamplingParams.extra_args`, and
`AdapterLogitsProcessor` wraps a per-request processor [S7]. A port
needs: the class registered at `LLM(...)` construction; gamma, delta,
and key per request in `extra_args`; the previous token per row from
the engine's output-token state; the bias as one batched scatter-add.
The pure core stays as is. Open: whether the vLLM ROCm build on DCS
supports custom processors.
