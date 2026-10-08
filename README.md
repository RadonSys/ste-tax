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

## Design

See `docs/design.md`. The intervention must be pinned first (prompt
instruction vs fine-tuning vs constrained decoding vs post-hoc rewrite),
because H1/H0 discriminate cleanly only under some of these. Compliance
needs a checker built from the extracted dictionary in `data/`.

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
    alternatives.
  - `rules.json`: the 53 writing rules of Part 1 with a paraphrase and the
    parameters a checker can enforce.
  - `manifest.json`: SHA-256 and byte size of each artifact.
- `scripts/build.py`: builds `data/`. Run: `uv run scripts/build.py`
  (uv reads `pyproject.toml`, pymupdf pinned in `uv.lock`).
- `docs/`: research design notes.

## License

MIT for original work. The ASD-STE100 PDF remains property of ASD; see
`LICENSE` section 3 for the educational-use basis.
