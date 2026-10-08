# Runbook: from node login to the results

This procedure gives the steps to operate the eval harness on the DCS
AMD nodes. Hardware data: `docs/dcs-amd-hardware.md`. Flags and output
fields: `eval/README.md`. Write the output of each command in your log.
The STE check of this file uses `docs/runbook.terms.txt`.

## 0. Before you get access

Get this data from the AMD lab manager (contact:
`docs/dcs-amd-hardware.md`, section 1):

1. The procedure to get an account for a student, with PI sponsorship.
2. The scheduler of the nodes, and the procedure to get one GPU.
3. The GPU-hour policy, and the maximum time for one job.
4. The ROCm version and the ROCm vLLM Docker image on the nodes. Can a
   user also put a different image on the nodes?
5. The egress of the nodes. Can the nodes download files from
   `huggingface.co` and from `cdn.jsdelivr.net`?
6. The location of the shared storage, and the GB that you can use. The
   checkpoints are 140 GB.

## 1. The `preflight` check

Do these steps on each node, in the ROCm vLLM image, from the
repository root:

```bash
git clone --recurse-submodules https://github.com/RadonSys/ste-tax.git
cd ste-tax
python3 -m eval preflight --backend vllm
```

1. On an MI350X node, make sure that the output shows `gfx950`.
2. Make sure that the output shows vLLM 0.29 or newer. Write the full
   vLLM version in your log.
3. If `preflight` gives exit 1, read each `problem:` item. Correct each
   problem before you start the harness.
4. On the MI100 node, use `--backend hf`, because vLLM cannot operate on
   the gfx908 GPU. Use the MI100 node only for software tests. Do not
   report a value from the MI100 node.

`preflight` writes a JSON file in `eval/results/`. The manifest of each
eval run also holds this data.

## 2. Get the checkpoints

If the nodes have no egress, download the checkpoints on a computer that
has a network connection. Then put the directories on the shared storage
of the cluster.

```bash
huggingface-cli download Qwen/Qwen3.8-27B --revision 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 --local-dir $STORE/Qwen3.8-27B
huggingface-cli download Qwen/Qwen3.5-9B --revision c202236235762e1c871ad0ccb60c8ee5ba337b9a --local-dir $STORE/Qwen3.5-9B
huggingface-cli download zai-org/GLM-4.7-Flash --revision 7dd20894a642a0aa287e9827cb1a1f7f91386b67 --local-dir $STORE/GLM-4.7-Flash
```

| Checkpoint | GB | Function |
| --- | --- | --- |
| Qwen3.8-27B | 55.6 | primary model |
| Qwen3.5-9B | 19.3 | small model |
| GLM-4.7-Flash | 62.5 | optional, only after a smoke test |

Make sure that each directory has the GB value of the table. Give the
directory to `--model`.

## 3. Prepare the checker

The checker is in the `.github/skills` submodule. It is necessary to
have `uv`. One time, the checker downloads its ste-tax release (v0.1.2,
from `cdn.jsdelivr.net`). The ROCm image has no `uv`, and the nodes can
have no egress. Thus, on a node, always use `--checker off`. After the eval
run, do the check on a computer that has `uv` and a network connection
(step 6).

## 4. Smoke test

Do the smoke test on one MI350X GPU for each Qwen model. The smoke test
of the 27B model is the first AMD test of that model.

```bash
python3 -m eval run --backend vllm --model $STORE/Qwen3.5-9B --limit 3 --samples 1 --checker off --run-id smoke-9b
python3 -m eval run --backend vllm --model $STORE/Qwen3.8-27B --limit 3 --samples 1 --checker off --run-id smoke-27b
```

The result is 9 records, a summary, and a directory in `eval/results/`.
If the smoke test stops with an error, the cause is the image, ROCm, or
the checkpoint. The same code operates correctly on the `mock` backend.

## 5. Full eval runs

Use one model on each MI350X node: Qwen3.8-27B on node 1, and Qwen3.5-9B
on node 2. Use one process for each GPU, and one task file for each
process. Do not change the decoding flags. The harness then uses the
sampling of the model card, 16384 new tokens, and 3 samples.

```bash
M=$STORE/Qwen3.8-27B; T=27b
HIP_VISIBLE_DEVICES=0 python3 -m eval run --backend vllm --model $M --tasks eval/tasks/gsm8k_full.jsonl --checker off --run-id $T-gsm8k &
HIP_VISIBLE_DEVICES=1 python3 -m eval run --backend vllm --model $M --tasks eval/tasks/math500.jsonl --checker off --run-id $T-math500 &
HIP_VISIBLE_DEVICES=2 python3 -m eval run --backend vllm --model $M --tasks eval/tasks/nq_open.jsonl --checker off --run-id $T-nq &
HIP_VISIBLE_DEVICES=3 python3 -m eval run --backend vllm --model $M --tasks eval/tasks/writing.jsonl --checker off --run-id $T-writing &
HIP_VISIBLE_DEVICES=4 python3 -m eval run --backend vllm --model $M --tasks eval/tasks/gsm8k_full.jsonl --prefix-caching --checker off --run-id $T-gsm8k-cache &
wait
```

On node 2, use `M=$STORE/Qwen3.5-9B; T=9b` and the same commands. The
GSM8K eval run has 15,828 outputs. Each of the 1,319 tasks has 3
samples, and each sample has 4 outputs (A0, A1, and two for A2).

## 6. The check and the summary

Put a copy of each `eval/results/<run-id>/` directory on a computer
that has `uv` and a network connection. Then, from the repository root:

```bash
uv run python -m eval rescore eval/results/27b-gsm8k
uv run python -m eval summarize eval/results/27b-gsm8k
```

Report the `gate_ok` rate with its two limits. On the examples of the
specification, it rejects 4.4% of the STE examples. It finds the error
in 89.1% of the Non-STE examples. Do not report the `checker_ok` rate
as the STE rate of an output. It rejects 44.8% of the STE examples.
