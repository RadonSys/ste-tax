# Intervention pin

Pin two arms before any measurement. Run all three axes on each arm.

## Recommended arms

- **A0: free-form baseline.** Same tasks, no STE instruction. Anchor for
  all comparisons.
- **A1: prompt instruction.** System prompt: "write in ASD-STE100 STE",
  with the dictionary attached. Measures the realistic deployment path.
- **A2: post-hoc rewrite.** Free-form draft first, second pass rewrites it
  into STE. Holds reasoning fixed. Isolates the compliance tax. Cleanest
  H1/H0 discriminator.

Order: A0, then A2, then A1. A2 gives the clean tax number first. A1 then
tests whether asking upfront costs more or less than fixing after.

## Deferred, with reason

- **Fine-tuning.** Measures training, not inference cost. High build cost
  (STE corpus, GPU). Cannot isolate the compliance tax from a capability
  shift. Revisit only if A1/A2 show the tax is real and worth training
  away.
- **Constrained decoding.** Forces circumlocution by construction. It
  measures the decoder's struggle, not the model's. Needs a technical-term
  allowlist to avoid degenerate output. Phase 2, after the natural
  compliance cost is known.

## Confounds and mitigations

- A1: instruction-following varies by model. Noncompliance reads as
  capability loss. Mitigation: compliance checker gates inclusion. Report
  compliance rate separately from task accuracy.
- A2: the rewrite pass can silently fix reasoning errors, inflating A2
  accuracy. Mitigation: freeze the draft. Log diffs. Rewriter may change
  surface form per STE rules only. Flag any content change.
- Degeneracy: the model may refuse or emit short stub output instead of
  circumlocuting. Record refusal/degeneracy as a third outcome, not as
  low accuracy.
- Checker risk: the checker defines compliance. Arm comparisons survive
  checker error, but absolute compliance rates do not. Validate the
  checker on a hand-labeled sample before trusting absolutes.

## What would kill the design

If A2 cost is about equal to A0 cost with equal quality, H0 wins under
the cleanest arm. Then A1 noncompliance is an instruction-following
artifact, not a thinking tax. Stop there.

## Open decisions

1. Approve arm order A0/A2/A1, or reorder.
2. Task suite. Suggestion: checkable QA benchmarks plus one open-ended
   technical-writing task.
3. Model set. Suggestion: one frontier reasoning model plus one smaller
   model, to test whether the tax scales with size.
