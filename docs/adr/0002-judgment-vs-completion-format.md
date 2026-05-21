# ADR-0002: Judgment-eliciting Q&A, not chunk-as-completion

> **Summary.** Every Q&A pair in this corpus must elicit *framework application*, not complete a chunk of source text verbatim. The Q states a situation; the A names the framework, applies it, and reaches a Decision. This is the inversion of Phase 0's chunk-as-completion shape, which taught voice (Markdown structure, だ/である tone, line vocabulary) without teaching what that vocabulary *does*. The shape is encoded as four per-pair invariants and a four-value `meta.shape` vocabulary that allows shape-stratified ablation in any downstream use.

## Status
accepted

## Date
2026-05-20

## Context

The Phase 0 `disposition-lora` prototype generated training pairs by the simple template "given article title T, generate section S." Each pair's Q was the article title plus a positional hint (`「{title}」というタイトルで、以下のセクションを書いて (全 N セクション中の i 番目)。`) and the A was the section body. This is the chunk-as-completion shape: the A is a verbatim chunk of source text, and the model's optimization target is "given title context, complete the section the way the original article did."

ADR-0001 records the LoRA outcome of this shape: voice transferred (Markdown headers, bullet/table layouts, だ/である 発見調 tone, AKC vocabulary) but **content was hallucinated**. The retrospective at `docs/empirical/README.md` Observation 1 phrases this as the "mannerism wrapper" failure mode.

The diagnostic question is *why* chunk-as-completion produces this pattern. The training loss is minimized when the model learns to reproduce surface features that are statistically frequent across chunks — Markdown headers, bilingual punctuation, characteristic discourse markers. The structural reasoning (Context → Decision → Consequence shape; the explicit invocation of `Emptiness` or `prohibition-strength` to make a choice; the recognition of which framework applies to a given situation) is *latent* in the source chunks but never made an explicit optimization target. The model has no gradient pointing at "name the framework and apply it" because no pair's loss penalizes failure to do so.

A judgment-eliciting shape changes the optimization target. If the Q states a *novel situation* and the A is expected to *name a framework and reach a Decision*, the loss penalizes pairs where the model produces line-adjacent vocabulary without applying the framework. Vocabulary alone no longer minimizes the loss; framework application does.

This corpus exists to encode the *judgment* of four research lines (AKC / Contemplative Agent / AAP / Authorship Strategy). Voice transfer was never the goal — the goal is that a model trained on this material can be asked "what would this line's framework say about situation X" and produce an answer that names the line's framework and reaches a Decision consistent with the line's documented stance.

## Decision

Every pair in `corpus/v0.1.0/{train,valid,pilot}.jsonl` must satisfy **four invariants**:

1. **Situation in the Q.** The Q presents a concrete situation — a problem, an architectural choice, a misconception, a behavior pattern — not a chunk-context prompt. The Q is *novel* in the sense that it is not a verbatim copy of the source ADR's `Context` section (enforced for `judgment` shape pairs by `scripts/validate_judgment.py` Layer 1 `q_novelty` check).

2. **Framework explicitly applied in the A.** The A invokes the line's documented framework by name (three-axis inversion / six-phase cycle / four contemplative axioms / four Business AI Quadrants / prohibition-strength hierarchy / etc.) and walks through the application. "Name and walk" is the load-bearing structure — naming alone is decoration (ADR-0004 §Problem 2 records why keyword presence is insufficient).

3. **Metadata carried.** Each pair has `meta.{line, source, lang, shape}` with `line ∈ {akc, contemplative-agent, aap, authorship-strategy, cross-line, zenn}`, `lang ∈ {en, ja}`, `shape ∈ {judgment, explain, definition, contrast}`, and `source` as a repo-relative path with optional `#fragment`. Metadata is auxiliary to the training signal but load-bearing for downstream ablation.

4. **Bilingual where the source is bilingual.** Each pair exists as two entries (EN + JA) with the same `meta.source` and `meta.shape` but different `meta.lang`. Detail is in ADR-0003.

### Shape vocabulary

| `meta.shape` | Q form | A form | Primary use |
|---|---|---|---|
| `judgment` | "Given situation X, how should one decide?" | Applies framework, names the Decision | ADR `Context` → `Decision` mapping; the core value-add of this corpus |
| `explain` | "What is X?" / "How does X work?" | Direct exposition | Thesis sections, structured prose from source |
| `definition` | "What does the term X mean in line Y?" | Glossary entry, one paragraph | Glossary terms |
| `contrast` | "How do line X and line Y differ in approach to situation Z?" | Cites both frameworks, names the divergence | Cross-line clarifications |

`judgment` is the primary shape and the highest-value content. The other shapes are retained — not removed — because they encode information the source files contain (definitions, theses, expository sections) that is *coherent with* the judgment material rather than competing with it. The `meta.shape` field exists precisely so that any consumer can stratify their consumption by shape (RAG by `shape == judgment`, training ablation by `shape ∈ {judgment, contrast}`, etc.).

### What this is not

- Not a refusal to include explanatory prose. `explain` and `definition` pairs are reusable from the source nearly verbatim; they are still legitimate corpus content.
- Not a guarantee that training on this corpus produces judgment transfer at any given (data scale, base model, iteration budget) point. ADR-0005 records that 851 pairs on Qwen3-8B-4bit at 300 iter does *not* clear that bar; the corpus structure is necessary but not sufficient for training-time judgment transfer at small scale.
- Not a per-pair rubric for human readers. The shape determines optimization-target behavior under training; humans reading individual pairs see them as well-formed Q&A regardless of shape.

## Alternatives considered

**Chunk-as-completion (Phase 0 default).** Rejected per the empirical evidence summarized above. Voice-only transfer at small data scale produces an artifact strictly weaker than just reading the source directly.

**Free-form completion (Q is unstructured, A is whatever follows).** Rejected. Free-form completion is what base-model pretraining already does; an instruction-tuning corpus that does not impose structure on the A field adds no signal the base model does not already have.

**Judgment-only (drop `explain` / `definition` / `contrast` shapes entirely).** Considered. The argument for is that the 27% / 73% split between `judgment` and other shapes in v0.1.0 may have caused the LoRA to learn the dominant shape (`explain`) at the cost of the rare shape (`judgment`) — ADR-0005 raises this as one of two open hypotheses for the Stage D FAIL. The argument against is that removing `explain` / `definition` / `contrast` strips information the corpus's primary audience (LLM-mediated diffusion consumers, including in-context RAG users) actually wants. The judgment-only ablation is a v0.2.0 experiment under `meta.shape` stratification, not a structural redesign here.

**Two-step Q&A (Q states situation; A first explains the framework, then applies it).** Considered and partially adopted. Many `judgment` pairs do walk through the framework in the A, but the format is not mandated as a two-paragraph split — the LLM-as-judge rubric (ADR-0004 Layer 2) evaluates whether the framework was applied, not whether it was applied in a particular paragraph layout.

## Consequences

### Immediate (structural)

- `scripts/extract_judgment_qa.py` and `scripts/prepare_judgment_prompts.py` generate situation-novel Qs paired with framework-naming As, not title-context Qs paired with section chunks.
- `scripts/validate_judgment.py` enforces a `q_novelty` check (Q must not contain the source ADR's Context first 200 characters verbatim) and a `q_anti_chunk` regex (forbid `"write a Zenn article"`, `"explain ADR-N"` patterns) — both Layer 1 fire-alarm signals that an extracted pair has regressed to chunk-as-completion shape.
- `scripts/line_templates.yaml` declares the per-line `judgment_synthesis_framework_keywords` (the framework terms each line's `A` should be anchored against). This is a *positive* signal — does the A reach for the right vocabulary — not a sufficient check; ADR-0004 Layer 2 rubric handles the sufficient check.
- `eval/prompt_bank.yaml` is also structured around situation-novel prompts with `expected_framework_keywords` and `expected_decision_pattern` fields, so the verification probe (Stage D) tests the same shape the corpus encodes.

### Downstream

- The corpus is usable for both RAG (where `meta.shape == judgment` is the retrieval target for "how would this line decide X" queries) and for training (where the full mix shapes general competence and the judgment shape pushes framework application specifically).
- Future corpora following this convention can be assembled mechanically (extractor scripts produce shape-tagged pairs) while still passing the shape-correctness checks.

### Risk

- A pair can be shape-correct (situation in Q, framework named in A) and still wrong about the framework's stance on the situation. Layer 1 (script) cannot catch this; Layer 2 (rubric agent, ADR-0004) is the explicit answer. Hand-review per round is mandated by the `CLAUDE.md` "Judgment generation protocol" section.

## Lineage

- Phase 0 retrospective: `base-model-lab/experiments/disposition-lora/findings.md` "Behavioral shift" table (2026-05-06)
- Empirical layer record: `docs/empirical/README.md` Observation 1
- Companion invariants: ADR-0001 (corpus as primary artifact), ADR-0003 (bilingual pair policy)
- Companion process: ADR-0004 (rubric-based validation), ADR-0005 (Stage D FAIL verdict — which the verification LoRA reproduces in the *output* what this ADR prohibits in the *input*)
