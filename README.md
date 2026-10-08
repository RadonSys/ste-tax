# ste-tax

What does it cost a large language model to write in Simplified Technical English?

## Research question

ASD-STE100 Simplified Technical English (STE) is a controlled natural
language for technical documentation: 53 writing rules plus a dictionary in
which each approved word carries exactly one meaning and one part of speech,
with synonyms collapsed to a single choice. This project measures whether
forcing LLM output into STE meaningfully affects three axes:

1. **Intelligence.** Task accuracy and output quality under STE constraint
   vs free-form generation on the same tasks.
2. **Cost.** Tokens (output + reasoning) and latency required to reach
   STE-compliant output, on local open-weight models.
3. **Watermark.** Detectability of statistical output watermarks under
   STE's constrained vocabulary.

## Hypotheses

- **H1 (it will matter).** The restricted word list forces circumlocution:
  the model burns thinking budget avoiding non-approved words, inflating
  token counts and degrading quality.
- **H0 (it won't matter).** The model plans in its native representation
  and constrains only the surface form at low cost; the standard is deeply
  enough represented in parameters that compliance is cheap.

## Design

See `docs/design.md` (prior work and gap, axes, checker) and
`docs/intervention-pin.md` (arms A0 free-form, A2 post-hoc rewrite, A1
prompt instruction). Models: Qwen3.8-27B and Qwen3.5-9B on one AMD
MI350X each (`docs/experiment-plan.md`, `docs/dcs-amd-hardware.md`).
Cost runs the full GSM8K test split; accuracy a 200-item MATH-500
sample (`docs/tasks.md`). Decoding: the vendor's thinking-mode
sampling, 16384 new tokens, 3 samples per task. Compliance: the
asd-ste100 checker, reported as the validated `gate_ok` beside raw `ok`
(`docs/checker-validation.md`). The watermark axis waits for the cost
result (`docs/advisor-review.md`).

## Run

    git clone --recurse-submodules https://github.com/RadonSys/ste-tax.git
    uv run python -m eval run --backend mock --decoding greedy   # plumbing
    uv run pytest

On the DCS nodes: `docs/runbook.md`. Harness reference:
`eval/README.md`.

## Repo layout

- `artifacts/ASD-STE100_ISSUE9.pdf`: the specification, committed under the
  educational-use grant documented in `LICENSE` section 3. Canonical source:
  https://www.asd-ste100.org/
- `data/`: machine-readable artifacts built from the specification. Each
  carries `schema_version` and a `source` block:
  - `dictionary.json`: every headword of Part 2 with part of speech,
    qualifier, forms, approved meaning or alternatives, help, examples.
  - `lexicon.json`: compact, lowercase lexicon for a checker: approved
    words with every form, and unapproved words mapped to approved
    alternatives, with the spec's help text.
  - `rules.json`: the 53 writing rules of Part 1 with a paraphrase and the
    parameters a checker can enforce.
  - `manifest.json`: SHA-256 and byte size of each artifact.
- `scripts/build.py`: builds `data/`. Run: `uv run scripts/build.py`
  (uv reads `pyproject.toml`, pymupdf pinned in `uv.lock`).
- `scripts/verify.py`: checks `data/`. Run: `uv run scripts/verify.py`.
- `scripts/checker_validation.py`: validates the asd-ste100 checker on
  the spec's own examples (`docs/checker-validation.md`).
- `eval/`: the harness (`python -m eval`), task files under
  `eval/tasks/`, the gate's H list `eval/gate_h.json`.
- `tests/`: pytest suite for the harness.
- `.github/skills`: the SKILLs repository as a submodule; the checker
  lives at `asd-ste100/`.
- `docs/`: design, plan, runbook, hardware, tasks, reviews, and
  `docs/friction/` ledgers.

## License

MIT for original work. The ASD-STE100 PDF remains property of ASD; see
`LICENSE` section 3 for the educational-use basis.
