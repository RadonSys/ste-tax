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
2. **Cost.** Tokens (output + reasoning), latency, and spend required to
   reach STE-compliant output.
3. **Watermark.** Detectability of statistical output watermarks under
   STE's constrained vocabulary.

## Hypotheses

- **H1 (it will matter).** The restricted word list forces circumlocution:
  the model burns thinking budget avoiding non-approved words, inflating
  token counts and degrading quality.
- **H0 (it won't matter).** The model plans in its native representation
  and constrains only the surface form at low cost; the standard is deeply
  enough represented in parameters that compliance is cheap.

## Design notes

See `docs/design.md`. The short version: the intervention must be pinned
first (system-prompt instruction vs fine-tuning on STE vs constrained
decoding against the dictionary vs post-hoc rewrite into STE), because
H1/H0 discriminate cleanly only under some of these. Compliance needs a
checker built from the extracted dictionary in `data/`. On the watermark
axis, green-list watermarks need per-token entropy; a controlled vocabulary
crushes entropy, so detectability should drop, and STE paraphrase doubles
as a watermark-stripping attack experiment.

## Repo layout

- `artifacts/ASD-STE100_ISSUE9.pdf`: the specification, committed under the
  educational-use grant documented in `LICENSE` section 3. Canonical source:
  https://www.asd-ste100.org/
- `data/ste100_dictionary.csv`: word list extracted from Part 2 of the
  specification (word, part of speech, approval status, approved meaning).
- `scripts/extract_dictionary.py`: the parser that produced `data/`.
- `docs/`: research design notes.

## Conventions (this repo only)

- Work directly on `main`.
- No force push. History is append-only: every commit pushed to `main` is
  preserved, never rewritten.
