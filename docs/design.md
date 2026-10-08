# Research design

## Interventions (pin these before measuring anything)

"Applying STE" is underspecified. Candidate interventions, ordered by how
strongly they constrain the model:

1. **Prompt instruction.** System prompt: "write in ASD-STE100 STE", with
   or without the dictionary attached.
2. **Fine-tuning.** Train on STE-compliant corpora; measure whether the
   style becomes "native" (cheap) or stays effortful.
3. **Constrained decoding.** Restrict generation to the approved word list
   (`data/lexicon.json`) plus declared technical terms.
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

- Output tokens, reasoning/thinking tokens, wall-clock latency, API spend
  per task, STE vs free-form.
- Mechanism check: does token inflation come from circumlocution (more
  words to say the same thing) or from retries/repairs?

### Watermark

- Apply a standard green-list watermark; measure detection z-scores on
  free-form vs STE-constrained outputs at matched lengths.
- Prediction: constrained vocabulary reduces per-token entropy, weakening
  detection. Null result is informative too.
- Bonus experiment: STE paraphrase as a watermark-stripping attack.

## Compliance checker

Built from `data/lexicon.json` and `data/rules.json`: tokenize output, flag words not in
the approved list (minus declared technical nouns/verbs), flag
unapproved parts of speech and meanings where detectable. This is what
makes the "STE condition" checkable rather than vibe-based.
