# eval

Eval harness for the STE-tax experiment. Design: ../docs/design.md,
../docs/intervention-pin.md, ../docs/experiment-plan.md.

- `harness.py`: runs arms A0 (free-form), A2 (post-hoc rewrite), A1
  (prompt instruction) over the task set. Records accuracy, reasoning
  tokens, generated tokens, latency, compliance, degeneracy per task.
  Backends: `mock` (no model), `hf` (transformers), `vllm` (cluster).
  `--watermark` runs the green-list sub-experiment (hf backend).
- `watermark.py`: green-list watermark generation bias and z-score
  detector (Kirchenbauer et al. 2023).
- `tasks.jsonl`: starter task set. Math and QA carry checkable answers;
  writing tasks are unscored.
- `results/`: run outputs, one JSONL per run. Not committed.
