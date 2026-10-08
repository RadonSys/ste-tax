# eval

Eval harness for the STE-tax experiment. Design: ../docs/design.md,
../docs/intervention-pin.md, ../docs/experiment-plan.md. Hardware and
cluster procedure: ../docs/dcs-amd-hardware.md.

## Run

Run from the repo root. `eval/` is a package. The core and the mock
backend need the standard library only.

    uv run python -m eval tasks                        # validate task files
    uv run python -m eval run --backend mock           # plumbing test
    uv run python -m eval summarize eval/results/<run-id>
    uv run python -m eval rescore eval/results/<run-id>
    uv run pytest

Real-model smoke on CPU (fixture model only, never on the dev box):

    uv run --extra hf python -m eval run --backend hf \
      --model Qwen/Qwen3.5-0.8B --limit 2 --max-new-tokens 192

Cluster, inside AMD's ROCm vLLM image (vllm comes from the image. This
project has no vllm extra, because the PyPI wheel targets CUDA):

    python3 -m eval run --backend vllm --model Qwen/Qwen3.5-9B --limit 3 --checker off
    python3 -m eval run --backend vllm --model Qwen/Qwen3.8-27B --checker off

Then copy `eval/results/<run-id>/` to a machine with uv and network, and
run `rescore`. With uv and network on the node, drop `--checker off`.

## Modules

- `harness.py`: pure core. Prompts, arms, answer check, degeneracy,
  reasoning split, summary. Effects enter only through `generate`.
- `records.py`: typed records and their JSON parsers.
- `loader.py`: task files to validated tasks, and seeded sampling.
- `compliance.py`: naive vocabulary rate, and the asd-ste100 checker adapter.
- `backends.py`: `mock`, `hf`, `vllm`. Heavy imports inside each adapter.
- `cli.py`: the shell. Arguments, files, manifest, environment capture.
- `watermark.py`: green-list watermark and z-score (Kirchenbauer et al.
  2023). `run --watermark`, hf backend only.

## Tasks

Default set: `eval/tasks.jsonl`, then every `eval/tasks/*.jsonl` by name.
`--tasks GLOB` replaces the set. Repeat it for more globs. `--limit N`
draws N tasks with seed `--sample-seed` (default 0) and keeps file order.

One JSON object per line:

| Key | Type |
| --- | --- |
| `id` | non-empty string, unique over all files |
| `kind` | `math`, `qa`, or `writing` |
| `prompt` | non-empty string |
| `answer` | math: finite number. qa: non-empty string. writing: null |
| `technical_terms` | list of non-empty strings. Multi-word terms are allowed |
| `source` | dataset name, or `handwritten` |
| `split` | non-empty string |
| `license` | non-empty string, SPDX id where one exists |
| `meta` | optional object. The harness ignores it |

Any other key is an error. The loader reports every error in every file,
then exits 1. Scored prompts must ask for a final line `Answer: <value>`.

## Output

`eval/results/<run-id>/`, run id `<backend>-<model>-<UTC time>` or
`--run-id`. An existing directory is an error.

`manifest.json`: run id, mode (`arms` or `watermark`), model, backend,
arms, seed, every config value, task file and lexicon SHA-256, sampled
task ids, git commit and dirty flag of ste-tax and of the skills
checkout, environment (python, platform, host, torch / vllm /
transformers / accelerate versions, `rocminfo` and `rocm-smi` output or
null), start and finish times, and `rescored` after a rescore.

`records.jsonl`, one record per task, sample, and arm:

| Field | Meaning |
| --- | --- |
| `task_id`, `kind`, `arm`, `model`, `backend` | identity |
| `sample` | sample index 0..k-1; sample s runs every call with seed + s. Absent in old records: read as 0 |
| `correct` | answer-line verdict. No answer line is false. Null for writing |
| `fallback_correct` | set only with no answer line: gold found in the text. Never counted as correct |
| `degenerate` | under 2 word tokens, or a refusal opening |
| `truncated` | generation hit `--max-new-tokens` (A2: either pass) |
| `reasoning_tokens` | tokens inside the think segment |
| `generated_tokens` | all new tokens |
| `output_tokens` | final-text tokens |
| `latency_s` | wall clock of the generate call(s) |
| `compliance` | naive vocabulary rate, or null when nothing is scorable |
| `nonconforming` | words outside the approved list (max 50) |
| `checker` | `{status: checked, ok, findings, by_kind, words, version, mode, gate_ok, gate_findings}` or `{status: skipped, reason}` |
| `text` | final text, think segment removed |
| `rewrite` | A2 only: draft text, draft correctness, token split |

Token counts come from token ids when the backend has a tokenizer, else
from whitespace words (mock). A think segment opened by the chat
template (output holds only `</think>`) counts as reasoning.

Summary per arm: `k` samples, then each mean metric as mean±sd. The
metric is computed per sample index over the tasks, then averaged over
the k samples (avg@k); sd is the spread of the k per-sample values (0
for k = 1). Mean metrics: accuracy over scored records that are not
truncated, tokens, latency, naive compliance, checker `ok` rate,
`gate_ok` rate, mean findings. Counts (records, answer-line misses,
fallback hits, degenerate, truncated, checked) are sums over all
samples. Then each arm's tax against A0, on the means.

## Compliance

Three numbers per record:

- `compliance`: naive rate. Trie over `data/lexicon.json`
  (`scripts/validate.py`). Necessary, not sufficient: no part of
  speech, meaning, or writing rules.
- `checker`: `btm-asd-ste100 check` from the asd-ste100 skill, through
  its documented binding, one process per record, after generation, in
  a thread pool (`--workers`, default CPU count). Reads the ste-tax
  release the skill pins (v0.1.2 at SKILLs b663ba1; word data equal to
  `data/`). `findings` counts report findings: one per distinct
  unapproved word, one per long sentence, and so on.
- `checker.ok`: raw. Every finding rejects. It rejects 44.8% of the
  spec's own STE examples (docs/checker-validation.md), so an absolute
  rate from `ok` is invalid. Arm comparisons under one checker and one
  allow list stay valid; the error is the same kind in each arm, but
  not independent of the text.
- `checker.gate_ok`: the validated gate, gate row 4. It drops
  `not_approved` on a word not in `data/lexicon.json` (no headword
  link), `not_approved` on an H token (`eval/gate_h.json`, 93 tokens:
  homographs in the findings of two or more STE examples, such as
  fuel, pump, oil), and `ing_form`. Every other finding rejects. On the
  validation set: 4.4% STE false rejects, 89.1% headword recall. State
  both numbers beside any gate rate. `gate_findings` counts what is
  left. Pure: no `lookup` call. Replayed over the validation reports
  of 2026-10-08: 97 of 2197 STE rejects, equal to the table. H is
  in-sample; regenerate it with `scripts/checker_validation.py` (key
  `h` of its detail file) after a checker release.

Both allow each task's `technical_terms` (whole multi-word term, regular
plural), and the label `Answer` on math and qa. Numbers do not count.
`--skills` names the SKILLs checkout (default: the `.github/skills`
submodule). `--checker-mode` sets `description` (default) or `procedure`.
The checker downloads its release once per cache, so it needs network
the first time. A failed call records `skipped` with the error.
`rescore` retries it.

## Config defaults

| Flag | Default | Source |
| --- | --- | --- |
| `--arms` | `A0 A2 A1` | intervention pin order |
| `--decoding` | `thinking`: temperature 1.0, top-p 0.95, top-k 20, 16384 new tokens, 3 samples | Qwen3.8-27B card, Best Practices, thinking mode; docs/advisor-review.md |
| `--decoding greedy` | temperature 0, top-p 1.0, top-k off, 1024 new tokens, 1 sample | plumbing setting. Never a reported number: the cap truncates thinking output |
| `--temperature`, `--top-p`, `--top-k`, `--max-new-tokens`, `--samples` | from the preset; a flag overrides one field | this file |
| `--seed` | `0`; sample s uses seed + s | experiment plan |
| `--wordlist` | `ids`: the 879 approved `WORD (POS)` ids in the A1/A2 system prompt. `none`: the rule only | experiment plan, known limits |
| `--prefix-caching` | off: every call pays its full prefill (cold-prompt cost) | hardware doc, section 5 |
| `--no-thinking` | thinking on | experiment plan |
| `--tp` | `1` | hardware doc |
| vLLM `max_model_len`, `gpu_memory_utilization` | `32768`, `0.90` (fixed, in manifest): prompt plus 16384 new tokens | hardware doc, KV cache |
| `--checker` | `cli` | this file |
