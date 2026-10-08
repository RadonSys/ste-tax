# Literature review: controlled natural languages as targets or constraints for LLM generation and evaluation

Question: how have controlled natural languages (ASD-STE100 Simplified
Technical English, Basic English, Attempto Controlled English, Caterpillar
Technical English, and similar) been used as targets or constraints for
large language model generation and evaluation, and what effects on output
quality, compliance, or cost are reported?

Skill: `/lit-review full` (SKILLs library). Session
`controlled-language-llm-48au6k7dsug0pjaf0bnnbpkabo`.

## Summary

The earlier review (docs/lit-review.md) found no paper on a fixed
controlled vocabulary like STE. A search aimed at the controlled-language
literature refutes that in part. Three independent groups put ASD-STE100
in front of a neural model: an LLM benchmark of STE-lexicon conformity, an
NMT decoder that swaps STE forbidden words, and a fine-tuned 7B model that
technical writers judged closer to STE. A second strand makes LLMs emit
rule-defined varieties such as German Easy Language; output moves toward
the standard but falls short of it. A third strand uses a controlled
language as an intermediate representation for semantic parsing and code
generation, with gains in data efficiency and correctness. A fourth, older
strand studies controlled-language pre-editing for machine translation,
with rule effects that differ by rule and by system. The gap that matters
for ste-tax stands: none of the 17 included papers measures the output
tokens, reasoning tokens, or latency a model spends to write in a
controlled language, none uses STE Issue 9, and none compares intervention
types for one controlled language.

## Method

Full-level scoping review, as of 2026-10-08. Sources: OpenAlex (12 keyword
queries), arXiv (6), Crossref (3), and two snowball rounds through OpenAlex
(8 seed calls, forward and backward). Queries aimed at the
controlled-language literature itself: exact phrases "ASD-STE100",
"Simplified Technical English", "Attempto Controlled English",
"Caterpillar Technical English", "controlled natural language" with
language-model terms, "controlled language" with neural MT, and
"specialized lexicon"; Crossref queries reached technical-communication and
translation venues. Truncated searches are ranked samples: "Simplified
Technical English", 100 of 168 upstream (plus all 88 from 2022 on);
"ASD-STE100", 100 of 105; "controlled natural language" with LLM, 50 of
1,213; Crossref queries, 40 each of millions (relevance-ranked). The arXiv
phrase search for "simplified technical english" (log s11) and the arXiv
search for "lexical constraints" with "technical writing" (s24) returned
zero records. OpenAlex calls ran without an API key.

Inclusion: a named controlled natural language with an explicit rule set
or fixed vocabulary as generation target, decoding constraint, rewriting
target, or evaluation criterion for a neural model, or a measure of
controlled-language compliance or quality of machine output; empirical;
2017 or later; English. Exclusion: controlled-language design or formal
semantics with no neural model; rule-based checkers; generic plain-language
simplification with no named standard; attribute-controlled generation;
formal target languages; non-empirical forms; non-English. Two amendments,
both 2026-10-08: theses admitted as labelled gray literature, because the
one industrial LLM-plus-STE study is a thesis; and the split between
controlled-language pre-editing for neural MT (included, natural-language
output measured) and controlled language fed only to a formal parser
(excluded) made explicit.

Flow: 846 records fetched; 514 after deduplication; 488 excluded at title
and abstract with reasons; 9 excluded at full-text triage as inaccessible
(no abstract in any index, publisher page blocked); 17 included. Read
level: 1 full text ([8]), 16 abstract.

## STE as a constraint or target for neural models

Three groups from different institutions use ASD-STE100 with a neural
model [2], [3], [8]. SpeciaLex, read in full, builds 1,785 test instances
over 18 subtasks; its STE part uses the Issue 7 lexicon to test "specific
role" and "special definition" constraints through checking,
identification, rewriting, and open generation [8]. Across 15 models up to
GPT-4o, GPT-4o and GPT-3.5-Turbo score best on the STE constraints, and
Llama3-70B shows no significant difference from them on STE checking and
identification (paired t-test, p > 0.05) or on STE rewriting and generation
(p > 0.05) [8]. Models asked to list words outside a lexicon list too few
[8]. One NMT study, abstract level, detects STE forbidden words with an
evidence-theory module and replaces them by same-part-of-speech
substitution or re-decoding; it reports +1.92 BLEU and +0.53 BLEURT over
baselines on two technical-publication test sets [2]. A master's thesis at
Saab Aeronautics fine-tunes Mistral-7B-Instruct with QLoRA on
expert-collected procedures; experts preferred its output 68% of the time
and named STE adherence as the main gain [3]. A fourth paper fine-tunes
LLMs to answer questions about ASD-STE100 Issue 9, with BLEU and ROUGE
gains for Qwen2.5-7B; it tests knowledge of the standard, not compliant
output [1]. Appraisal: [8] has the strongest design; [3] is a thesis with
a qualitative compliance judgment; [2] reports translation quality, not a
compliance rate. None of the four reports a cost measure.

## Rule-defined controlled varieties as LLM output

One study, abstract level, prompts ChatGPT to translate German
administrative texts into Easy Language; output is easier than the source
but does not fully meet Easy Language standards and is not always correct
in content [11]. Another fine-tunes language models on Easy Language text
and reports more accessible simplifications with less parallel data [16].
A proof of concept generates controlled-language assembly instructions
from product-process-resource models with an LLM and RAG; its authors
limit it to two use cases and one model [6]. A healthcare system paper
reports gains in clarity and usability from an AI controlled-language
system [12]; its venue and unclear method give it little weight. The two
Easy Language papers [11], [16] come from different groups and agree that
models move toward the variety; only [11] measures conformance to the
standard, and it finds a shortfall.

## Controlled language as an intermediate representation

Generating a controlled natural language helps downstream structured
tasks. One group reports, in two papers, that LLMs parse into controlled
natural languages for knowledge-graph question answering with less
training data than parsing into SPARQL, and more accurately at equal data
[4], [5]; this is one group's position. NL2ASP uses neural translation into
controlled-language statements before a rule-based step to answer-set
programs [7]. A hardware-design workflow uses Gherkin-style controlled
specifications and reports 2.48x functional correctness and 2.54x formal
coverage over other LLM methods [14]. Independent support for the
intermediate-representation benefit comes from three groups [4], [7],
[14], on different tasks and metrics.

## Controlled-language pre-editing for machine translation

Controlled-language rules applied to source text generally improve MT
output, with qualifications. A mixed-methods study of German technical
text across five MT systems finds a positive overall effect, but per rule
four rules helped, three hurt, and two had no significant effect; rules
that helped earlier MT did not help NMT, and NMT gave the best output with
or without the rules [10]. Four controlled Chinese rules improved
Chinese-English MT adequacy, fluency, and style on one product description
[15]. Error analysis of 23 students' Japanese essays under NMT yields five
pre-editing principles [17]. DeepL handles formulaic German under lexical
controlled-language rules with stable strategies [9]. The studies disagree
on the size of the benefit for NMT: [10] reads its result as NMT no longer
needing the rules, while [15] reports significant gains on NMT-era output.
The visible cause is scale: [15] tests one text.

## Token cost of a controlled language

One study measures tokens: Telegraph English, a symbol-rich controlled
dialect, rewrites prompts to about 50% of their tokens and keeps 99.1% key
fact accuracy with GPT-4.1 on 4,081 LongBench-v2 pairs [13]. That is
compression of model input, the opposite direction from ste-tax, where the
constraint applies to model output.

## Limitations of this review

Sixteen of 17 papers were read at abstract level; numbers are the authors'
abstract claims, except [8]. Nine relevant-looking records were
inaccessible and are unassessed, among them two 2025 chapters on LLMs for
Easy German (doi:10.1007/978-3-032-02813-6_15,
doi:10.1007/978-3-032-02813-6_20) and Marzouk and Hansen-Schirra 2019 on
controlled language and NMT (doi:10.1007/s10590-019-09233-w). Technical
communication journals (Technical Communication, IEEE Transactions on
Professional Communication, Journal of Technical Writing and Communication)
were reached only through OpenAlex and Crossref indexing; no direct venue
search ran. Crossref ranking returned mostly noise. OpenAlex ran keyless.
Work in German, Spanish, Turkish, Finnish, and Russian was excluded by the
language criterion, and the controlled-language-for-MT literature is
larger in those languages. SpeciaLex's own later venue version is not in
the corpus. The thesis record [3] has no DOI; its handle page sits behind a
bot check, so its identity rests on the OpenAlex record.

## Gaps and open questions

- None of the 17 included papers measures the output-token, reasoning-token,
  or latency cost of producing text in a controlled language; the one
  token measurement [13] compresses input (probes s5, s6, s11, s24).
- None uses ASD-STE100 Issue 9 as a generation constraint; [8] uses Issue
  7, and [1] uses Issue 9 only as a question-answering subject.
- None compares prompt instruction, fine-tuning, constrained decoding, and
  post-hoc rewrite for one controlled language; [8] prompts, [3]
  fine-tunes, and [2] constrains decoding, each alone.
- None tests watermark detection on controlled-language output.
- None reports a compliance rate from an automatic checker over the full
  STE rule set; [8] scores lexicon conformity only.

## Included papers

| [n] | Title | Authors | Year | Venue | Read | Key |
| --- | --- | --- | --- | --- | --- | --- |
| [1] | Research on English Large Language Model for Aviation Professionals Based on Lora Fine-Tuning | Fan and Li | 2025 | CEI | abstract | doi:10.1109/cei66465.2025.11398497 |
| [2] | An STE-Guided Machine Translation Method based on Evidence Theory | Ye et al. | 2025 | IJCNN | abstract | doi:10.1109/ijcnn64981.2025.11229095 |
| [3] | Expert in the Loop: LLM Assistance for Technical Documentation Writing Case Study at Saab AB | Nieminen | 2025 | Gothenburg University (thesis) | abstract | hdl:2077/87918 |
| [4] | Bridging language models and knowledge graphs with controlled natural languages | Bhandiwad et al. | 2026 | Knowledge-Based Systems | abstract | doi:10.1016/j.knosys.2026.115405 |
| [5] | Language Models as Controlled Natural Language Semantic Parsers for Knowledge Graph Question Answering | Lehmann et al. | 2023 | ECAI (FAIA) | abstract | doi:10.3233/faia230411 |
| [6] | Leveraging LLM for Assembly Instructions Using Controlled Natural Language | Jonek and Manns | 2026 | LN Mechanical Engineering | abstract | doi:10.1007/978-3-032-16889-4_64 |
| [7] | Towards Automatic Composition of ASP Programs from Natural Language Specifications | Borroto Santana et al. | 2024 | IJCAI | abstract | doi:10.24963/ijcai.2024/685 |
| [8] | SpeciaLex: A Benchmark for In-Context Specialized Lexicon Learning | Imperial and Tayyar Madabushi | 2024 | arXiv | full-text | arxiv:2407.13297 |
| [9] | Formulaicity of German Controlled Language as a Translation Challenge for Neural Machine Translation | Manerova | 2025 | Nauchnyi Dialog | abstract | doi:10.24224/2227-1295-2025-14-8-101-120 |
| [10] | An in-depth analysis of the individual impact of controlled language rules on machine translation output: a mixed-methods approach | Marzouk | 2021 | Machine Translation | abstract | doi:10.1007/s10590-021-09266-0 |
| [11] | Using ChatGPT as a CAT tool in Easy Language translation | Deilen et al. | 2023 | arXiv | abstract | arxiv:2308.11563 |
| [12] | Control Natural Language in healthcare | Marius | 2026 | IJRTI | abstract | doi:10.56975/ijrti.v11i6.212109 |
| [13] | Telegraph English: Semantic Prompt Compression via Structured Symbolic Rewriting | Arbuzov et al. | 2026 | arXiv | abstract | arxiv:2605.04426 |
| [14] | LLM-enabled Behavior Driven Development Workflow for Formally Verified Hardware Designs | Müller et al. | 2026 | arXiv | abstract | arxiv:2609.15318 |
| [15] | Designing Controlled Chinese Rules for MT Pre-Editing of Product Description Text | Zheng et al. | 2022 | IJTIAL | abstract | doi:10.4018/ijtial.313919 |
| [16] | Language Models for German Text Simplification: Overcoming Parallel Data Scarcity through Style-specific Pre-training | Anschütz et al. | 2023 | Findings of ACL | abstract | doi:10.18653/v1/2023.findings-acl.74 |
| [17] | Pre-editing rules developed for higher-quality target language texts | Tsuji | 2024 | Journal of Modern Languages | abstract | doi:10.22452/jml.vol34no2.7 |
