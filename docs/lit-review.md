# Literature review: effects of constraining LLM output to a controlled vocabulary

## Summary

The literature covers output constraints on language models from two
traditions: constrained decoding (lexical, grammatical, structural) and
LLM watermarking. Constraints reliably enforce surface form but their
effect on task quality splits by fit: they raise accuracy when the
constraint matches the task and distort generation when model probability
mass conflicts with valid continuations. Latency costs of constrained
decoding are large and shrinking. Watermark detection degrades on
low-entropy text, which four independent groups address; paraphrase and
substitution attacks substantially weaken watermarks. No included paper
studies a fixed controlled vocabulary like ASD-STE100 directly: nothing
measures verbosity or reasoning-token cost under vocabulary restriction,
and no watermark study tests detection on vocabulary-restricted text.

## Method

Scoping review, full level, as of 2026-10-08. Sources: OpenAlex and
arXiv, via logged script queries. Seven search rounds ran: three OpenAlex
keyword rounds (constrained decoding quality; restricted-vocabulary cost;
watermark low-entropy and paraphrase), two arXiv rounds (watermark;
constrained decoding), and two backward snowball rounds from included
seeds. Truncated searches are ranked samples: s1 returned 30 of 9,848
upstream matches; s3, 30 of 265; s4, 30 of 209; s5, 30 of 121; s6, 25 of
50. One keyword round on verbosity and circumlocution returned a single
match. One snowball seed had no OpenAlex references (metadata gap).

Inclusion required: measured effects of output vocabulary or style
constraints on task performance, generation cost, or watermark detection;
lexically constrained decoding with measured quality or cost trade-offs;
watermarking evaluated under low-entropy text or paraphrase attack;
empirical results, 2018 or later, English. Exclusion removed: non-
vocabulary controlled generation (sentiment, toxicity, topic) without the
target outcomes; decoding algorithms with no quality or cost measurement;
abstracts only, editorials, non-English. Amendment 2026-10-08: watermark
inclusion narrowed to detection under low-entropy or constrained text,
the Kirchenbauer foundation and its direct evaluations, and at most two
representative papers per attack family, since the paraphrase-attack
subfield alone would dominate the shortlist.

Flow: 131 candidates identified; 104 excluded at title and abstract with
reasons; 0 excluded at full text; 27 included. Read level is abstract for
all 27. The included set runs slightly above the full-level band of 10 to
25; the three snowball additions are foundational constrained-decoding
papers meeting all criteria, so they were kept and the deviation is
disclosed here.

## Constrained decoding and task performance

Constrained decoding eliminates structural failures. One study benchmarks
five small models on 14 structured-output tasks and finds schema validity
rising from 78.6-92.9% to 100% under constrained decoding [22]. A second
study finds the same guarantee comes with a semantic gap: type coercion
errors are fixable by constraints while instruction-semantic failures in
multi-step function calling resist them. Schema conformance guarantees
form, not content [22].

Whether constraints help or hurt task accuracy depends on fit. Grammar-
constrained LMs without finetuning beat task-specific finetuned models on
information extraction, entity disambiguation, and constituency parsing
[4]. Template constrained decoding from historical query patterns raises
text-to-SQL execution accuracy up to 36% over in-context learning [21].
But when the model assigns low probability to valid continuations,
masking pushes decoding toward locally valid yet semantically wrong
trajectories; draft-conditioned decoding recovers up to 24 percentage
points of structured accuracy on GSM8K with a 1B model by separating
planning from enforcement [18]. A separate study of LLM self-correction
finds structural constraints trigger a new failure mode, "structure
snowballing," where the load of satisfying strict formats crowds out
error detection [20].

Wording interacts with constraints. One study varies only schema-key
wording under constrained decoding and finds substantial accuracy shifts,
positive and negative across seven models, with prompt-level and schema-
level instructions interacting non-additively [19]. A survey of
constrained text generation for LLMs categorizes constraints as lexical,
structural, and relation-based and documents both capacity and deficiency
in how LLMs incorporate them [3]. The pre-LLM foundations established
lexically constrained decoding with O(1) cost in constraint count [25],
batched decoding with 5x throughput [26], and terminology-constrained NMT
decoding [27].

## Cost of constrained decoding

Lookahead-based constrained decoding is effective and expensive. One
method replaces full lookahead rollouts with a small draft model plus
target-model verification and reports 2.2x to 12.15x speedup over the
lookahead baseline without significant performance loss [1]. Prefix-tree
constrained decoding is inefficient on GPUs and biases the output
distribution; a dynamic importance-sampling replacement claims asymptotic
unbiasedness with better efficiency [17]. Grammar-constrained decoding
work targets the tokenizer-to-grammar alignment cost [23]. Template
constrained decoding reports 2.2x lower latency on matched queries [21].
Entropy tagging for watermarking cut parameters 99% with a lightweight
extractor [8]. No included paper measures token-count inflation,
reasoning-token cost, or latency of a vocabulary restriction specifically.

## Watermark detection under low-entropy text

Low-entropy text degrades green-list watermark detection, and four
independent groups address it. Entropy-weighted detection gives high-
entropy tokens more influence and improves low-entropy detection without
training [6]. A lightweight feature extractor plus entropy tagger replaces
the source LLM for entropy estimation, cutting parameters 99% on code
benchmarks [8]. An unbiased sampling method preserves the token
distribution in expectation with lower risk of bad outputs in low-entropy
settings and needs no prompt or white-box model at detection time [11].
An entropy-guided threshold scheme reports over 80% improvements on math
benchmarks while keeping detection accuracy [7]. The Kirchenbauer green-
list scheme itself reports negligible quality impact with detection from
short spans [13]; a benchmark finds detection under 100 tokens on chat
models with no perceivable quality loss, but poor results on code [16].

## Watermark resistance to paraphrase and rewriting

Paraphrase and substitution substantially weaken watermarks. One study
shows claims of resistance to paraphrase fail once attackers reverse-engineer
the scheme from limited black-box generations, making paraphrase attacks
drastically more effective [5]. A color-aware substitution attack infers
green and red token sets by prompting and comparing frequencies, then
substitutes green tokens, removing the watermark with fewer edits than
prior work and, the authors claim, for arbitrarily long text [10]. A
unified platform integrating 10 watermarkers and 12 attacks systematizes
these results [9]. One defense derives watermark logits from semantic
embeddings of the full preceding context and reports resistance to
synonym substitution and paraphrasing [15]. Quality-preserving variants
exist: sparse watermarking on POS-anchored tokens [12] and multi-channel
unbiased watermarking with 10%+ detectability gains [14].

## Limitations of this review

All 27 included papers were read at abstract level; numbers quoted are
the authors' abstract-level claims. Truncated searches are ranked
samples, so relevant papers beyond the top 30 per query may be missed.
Sources were OpenAlex and arXiv only; ACL Anthology records entered via
OpenAlex indexing. The 2026 arXiv preprints are unreviewed. The watermark
attack literature was representatively sampled under the recorded
amendment, not exhausted. Three abstracts were retrieved from publisher
PDFs because the corpus records lacked them.

## Gaps and open questions

None of the 27 included papers measures verbosity, circumlocution, or
reasoning-token cost under a restricted output vocabulary; the dedicated
keyword round returned one match. None evaluates watermark detection on
text constrained to a fixed controlled vocabulary; low-entropy studies
use code or math instead. None measures task-performance effects of
vocabulary restriction as distinct from structural or grammar
constraints. None compares intervention types head to head: prompt
instruction, fine-tuning, constrained decoding, and post-hoc rewrite.
These four gaps map directly onto the ste-tax research design.

## Included papers

| [n] | Title | Authors | Year | Venue | Read | Key |
| --- | --- | --- | --- | --- | --- | --- |
| [1] | Constrained Decoding with Speculative Lookaheads | Nakshatri et al. | 2024 | arXiv | abstract | doi:10.48550/arxiv.2412.10418 |
| [2] | NeuroLogic A*esque Decoding: Constrained Text Generation with Lookahead Heuristics | Lu et al. | 2022 | NAACL | abstract | doi:10.18653/v1/2022.naacl-main.57 |
| [3] | Evaluating, Understanding, and Improving Constrained Text Generation for Large Language Models | Chen and Wan | 2023 | arXiv | abstract | doi:10.48550/arxiv.2310.16343 |
| [4] | Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning | Geng et al. | 2023 | EMNLP | abstract | doi:10.18653/v1/2023.emnlp-main.674 |
| [5] | Revisiting the Robustness of Watermarking to Paraphrasing Attacks | Rastogi and Pruthi | 2024 | EMNLP | abstract | doi:10.18653/v1/2024.emnlp-main.1005 |
| [6] | An Entropy-based Text Watermarking Detection Method | Lu et al. | 2024 | ACL | abstract | doi:10.18653/v1/2024.acl-long.630 |
| [7] | Entropy-Guided Watermarking for LLMs: A Test-Time Framework for Robust and Traceable Text Generation | Cai et al. | 2025 | arXiv | abstract | doi:10.48550/arxiv.2504.12108 |
| [8] | Invisible Entropy: Towards Safe and Efficient Low-Entropy LLM Watermarking | Gu et al. | 2025 | EMNLP | abstract | doi:10.18653/v1/2025.emnlp-main.341 |
| [9] | Watermark under Fire: A Robustness Evaluation of LLM Watermarking | Liang et al. | 2024 | arXiv | abstract | doi:10.48550/arxiv.2411.13425 |
| [10] | Bypassing LLM Watermarks with Color-Aware Substitutions | Wu and Chandrasekaran | 2024 | ACL | abstract | doi:10.18653/v1/2024.acl-long.464 |
| [11] | Watermarking Low-entropy Generation for Large Language Models: An Unbiased and Low-risk Method | Mao et al. | 2024 | arXiv | abstract | doi:10.48550/arxiv.2405.14604 |
| [12] | Less is More: Sparse Watermarking in LLMs with Enhanced Text Quality | Hoang et al. | 2024 | arXiv | abstract | doi:10.48550/arxiv.2407.13803 |
| [13] | A Watermark for Large Language Models | Kirchenbauer et al. | 2023 | arXiv | abstract | arxiv:2301.10226 |
| [14] | Improved Unbiased Watermark for Large Language Models | Chen et al. | 2025 | arXiv | abstract | arxiv:2502.11268 |
| [15] | A Semantic Invariant Robust Watermark for Large Language Models | Liu et al. | 2023 | arXiv | abstract | arxiv:2310.06356 |
| [16] | Mark My Words: Analyzing and Evaluating Language Model Watermarks | Piet et al. | 2023 | arXiv | abstract | arxiv:2312.00273 |
| [17] | Efficient and Asymptotically Unbiased Constrained Decoding for Large Language Models | Ye et al. | 2025 | AISTATS | abstract | arxiv:2504.09135 |
| [18] | The Hidden Cost of Structured Generation in LLMs: Draft-Conditioned Constrained Decoding | Reddy et al. | 2026 | arXiv | abstract | arxiv:2603.03305 |
| [19] | Schema-Key Wording as an Instruction Channel in Structured Generation under Constrained Decoding | Le | 2026 | arXiv | abstract | arxiv:2604.14862 |
| [20] | From Hallucination to Structure Snowballing: The Alignment Tax of Constrained Decoding in LLM Reflection | Zhou | 2026 | arXiv | abstract | arxiv:2604.06066 |
| [21] | Reliable Answers for Recurring Questions: Boosting Text-to-SQL Accuracy with Template Constrained Decoding | Jivani et al. | 2026 | PACM MGMT | abstract | doi:10.1145/3769822 |
| [22] | Constrained Decoding Eliminates Structural Failures in Small LLMs but Reveals a Scale-Dependent Semantic Gap | Chavan | 2026 | arXiv | abstract | arxiv:2609.23742 |
| [23] | Flexible and Efficient Grammar-Constrained Decoding | Park et al. | 2025 | arXiv | abstract | arxiv:2502.05111 |
| [24] | JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models | Geng et al. | 2025 | arXiv | abstract | arxiv:2501.10868 |
| [25] | Fast Lexically Constrained Decoding with Dynamic Beam Allocation for Neural Machine Translation | Post and Vilar | 2018 | NAACL | abstract | doi:10.18653/v1/n18-1119 |
| [26] | Improved Lexically Constrained Decoding for Translation and Monolingual Rewriting | Hu et al. | 2019 | NAACL | abstract | doi:10.18653/v1/n19-1090 |
| [27] | Neural Machine Translation Decoding with Terminology Constraints | Hasler et al. | 2018 | NAACL | abstract | doi:10.18653/v1/n18-2081 |
