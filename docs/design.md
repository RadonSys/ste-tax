# Research design

Pinned arms: docs/intervention-pin.md (A0, A2, A1). Models, tasks, and
decoding: docs/experiment-plan.md. Node procedure: docs/runbook.md.

## Prior work and the gap

docs/lit-review-cnl.md (2026-10-08, 17 papers) refutes in part the first
review's claim (docs/lit-review.md) that no paper puts a fixed
controlled vocabulary like STE in front of a model. Closest prior work,
three groups with ASD-STE100 and a neural model:

- SpeciaLex (Imperial and Tayyar Madabushi 2024, arXiv 2407.13297): an
  in-context benchmark of STE Issue 7 lexicon constraints over 15
  models; lexicon conformity only.
- An STE-guided NMT decoder that swaps STE forbidden words (Ye et al.
  2025, IJCNN); translation quality, not a compliance rate.
- A Mistral-7B fine-tune for Saab procedures (Nieminen 2025, thesis);
  expert preference, qualitative compliance.

The gap this project fills: none of the 17 papers measures the output
tokens, reasoning tokens, or latency of writing in a controlled
language; none uses STE Issue 9 as a generation constraint; none
compares intervention types (prompt, fine-tune, constrained decoding,
rewrite) for one controlled language. docs/lit-review-reasoning-cost.md
(10 papers) finds no study of the reasoning-token cost of a vocabulary
constraint.

## Interventions (pin these before measuring anything)

"Applying STE" is underspecified. Candidate interventions, ordered by how
strongly they constrain the model:

1. **Prompt instruction.** System prompt: "write in ASD-STE100 STE", with
   or without the dictionary attached.
2. **Fine-tuning.** Train on STE-compliant corpora; measure whether the
   style becomes "native" (cheap) or stays effortful.
3. **Constrained decoding.** Restrict generation to the approved word list
   (built from `data/lexicon.json`) plus declared technical terms.
4. **Post-hoc rewrite.** Free-form generation, then a second pass that
   rewrites into STE. Separates reasoning cost from compliance cost.

H1 vs H0 discriminate most cleanly under (1) and (4): (4) isolates the
compliance tax by holding reasoning fixed.

## Axes and operationalization

### Intelligence

- Same task suite, two conditions: free-form vs STE-constrained output.
- Metrics: task accuracy (benchmarks with checkable answers), plus blind
  human/LLM-judge quality ratings for open-ended tasks.
- Watch for: tasks where STE is near-impossible (heavy math notation,
  code); record as boundary cases, not failures.

### Cost

- Output tokens, reasoning/thinking tokens, wall-clock latency per task,
  STE vs free-form. Local open-weight models only: no API spend.
- Decoding: the vendor's thinking-mode sampling, a 16384-token budget,
  k = 3 samples per task; results are mean±sd over samples. Greedy
  with a 1024 cap truncates thinking output and is a plumbing setting
  only (docs/advisor-review.md).
- Mechanism check: does token inflation come from circumlocution (more
  words to say the same thing) or from retries/repairs?

### Watermark

- On hold until the cost claim returns (docs/advisor-review.md).
  Instrument as built: docs/watermark.md. Its recommendations (EWD
  detection, unique-pair z) are referenced, not implemented.
- Apply a standard green-list watermark; measure detection z-scores on
  free-form vs STE-constrained outputs at matched lengths.
- Prediction: constrained vocabulary reduces per-token entropy, weakening
  detection. Null result is informative too.
- Bonus experiment: STE paraphrase as a watermark-stripping attack.

## Compliance checker

The asd-ste100 checker (`btm-asd-ste100 check`, SKILLs repository,
vendored at `.github/skills`; it reads this repo's release v0.1.2 built
from `data/`). It flags words outside the approved list (minus declared
technical nouns and verbs), -ing forms, contractions, semicolons, and
sentence and paragraph length; it signals part-of-speech and passive
candidates; it does not examine meaning. `scripts/validate.py` keeps
the naive vocabulary rate for continuity.

Validated on the spec's own examples (docs/checker-validation.md): raw
`ok` rejects 44.8% of the 2197 STE examples, so absolute rates from it
are invalid; arm comparisons under one checker and one allow list
stand. The recommended gate drops findings on words not in the
dictionary, on 93 spec-attested homographs (H), and `ing_form`: 4.4%
STE false rejects, 89.1% headword recall. The harness reports it as
`gate_ok` beside raw `ok` (eval/README.md, Compliance). This is what
makes the "STE condition" checkable rather than vibe-based.
