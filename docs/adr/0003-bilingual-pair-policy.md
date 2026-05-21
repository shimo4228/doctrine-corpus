# ADR-0003: Bilingual pair policy (EN + JA as two separate pairs)

> **Summary.** Each judgment example exists as **two corpus entries** — one English, one Japanese — with identical `meta.source` and `meta.shape` but different `meta.lang`. They are not merged into a single bilingual pair, not augmented from a single canonical language, and not deposited as separate split files. The choice doubles the apparent corpus size, preserves the Authorship Strategy line's bilingual diffusion property, and keeps language as a first-class ablation axis via `meta.lang`.

## Status
accepted

## Date
2026-05-20

## Context

The four upstream research lines this corpus draws from are predominantly bilingual:

- AKC, Contemplative Agent, AAP, and Authorship Strategy each maintain an English-primary CLAUDE.md / README and Japanese `*.ja.md` translations of their ADRs, glossaries, and theses.
- The `zenn-content` repository is Japanese-primary (Zenn is a Japanese developer publishing platform) with no canonical English version.
- The author's audience spans Japanese-language Zenn readers and English-language researchers reading the DOI-deposited material via Zenodo / HuggingFace.

Three options were on the table at Stage A:

(1) **EN-only.** Use English source material; drop Japanese surface forms.
(2) **JA-only.** Use Japanese; drop English. (Symmetric to (1), but with the Zenn corpus included.)
(3) **Merged bilingual.** One pair per situation, with both EN and JA stitched into a single Q and a single A.
(4) **Two pairs per situation.** EN pair and JA pair as separate entries.

Each option has different consequences for (a) what the corpus says about language, (b) how downstream LLMs that consume it behave, and (c) whether the Authorship Strategy line's "LLM-mediated diffusion" property is preserved.

The Authorship Strategy framework explicitly identifies LLM-mediated channels (LLM-direct and LLM-mediated-human) as the primary audience and lists *creative reuse* (in-context, RAG, training) above *training* in the preference hierarchy. Both consumption paths benefit from a corpus that *demonstrates the same judgment in both languages*: an LLM running RAG against this corpus may retrieve either lang variant depending on the user's query language, and a training-stage consumer may decide to train on EN-only / JA-only / both via `meta.lang` filtering. Locking the corpus to one language closes off downstream consumption paths.

## Decision

Each judgment example is encoded as **two entries** in `corpus/v0.1.0/*.jsonl`:

```jsonl
{"messages": [...], "meta": {"line": "akc", "source": "docs/adr/0002.md#decision", "lang": "en", "shape": "judgment"}}
{"messages": [...], "meta": {"line": "akc", "source": "docs/adr/0002.md#decision", "lang": "ja", "shape": "judgment"}}
```

The two entries share `meta.source` (so they trace back to the same upstream artifact) and `meta.shape`. They differ in `meta.lang` and in the `messages` array's natural-language content.

### Equivalence requirements

For `shape ∈ {judgment, contrast}`:

- The EN and JA Q must present the **same situation**. Idiomatic translation is OK; substitution of an entirely different scenario is not.
- The EN and JA A must reach the **same Decision**. The named framework keywords (`judgment_synthesis_framework_keywords` per `scripts/line_templates.yaml`) appear in both, in their native form (e.g., `Emptiness` in EN, `Emptiness` or `空性` in JA per the line's glossary).
- ADR-0004 Layer 2 rubric criterion 6 ("Bilingual Pair Equivalence") explicitly checks this property; pairs that fail criterion 6 are WEAK/FAIL.

For `shape ∈ {explain, definition}`:

- The EN and JA pairs can be near-verbatim translations from the source's bilingual files (most line ADRs / glossaries have both). The equivalence bar is lower — the goal is parallel surface forms rather than independent judgment expressions — because these shapes are extracted from already-translated material.

### Single-language exceptions

Some sources exist only in one language and have no canonical other-language version. For these, only one `meta.lang` entry is produced:

- `meta.line == "zenn"`: Japanese only. Zenn articles do not have author-authored English versions; machine-translating Zenn content into English would introduce drift that ADR-0002 explicitly prohibits.
- Source ADRs that have not been translated yet (occasional): single-language entry, `meta.lang` reflects the source language.

In the v0.1.0 counts, this asymmetry shows as `by_lang: {en: 334, ja: 517}` — the JA surplus is mostly the 222 Zenn entries.

## Alternatives considered

**EN-only.** Rejected. The author's published Zenn material would be excluded entirely (no canonical English version exists), and the parent Authorship Strategy line's bilingual-by-design property would be discarded by the corpus. Downstream Japanese-language LLM consumption (a substantial audience for this author's work) would be served only via machine translation at retrieval time, which re-introduces the drift problem.

**JA-only.** Symmetric to EN-only; rejected for the same reasons in mirror. Additionally, the international research audience reading the DOI deposit on Zenodo would be served only via machine translation, which works against the LLM-mediated diffusion goal.

**Merged bilingual pair (one entry containing both languages).** Considered and rejected. The merged form (Q has both EN and JA situations, A has both EN and JA responses concatenated) makes the language axis invisible to `meta.lang` filtering — a downstream consumer who wants EN-only training data cannot recover it without language-detecting and re-splitting every pair. The merged form also creates loss-target weirdness during training: the model is optimizing across a single sequence that switches language mid-stream, which is not a representative input distribution.

**Bilingual as augmentation (JA generated mechanically from EN).** Considered and rejected. Authorship Strategy is explicit that translations are not augmentation noise but *first-class authorial decisions* — the JA form may differ in framing, choice of example, or relative emphasis. Mechanically generated JA from EN would propagate machine-translation drift into the corpus and undermine the "bilingual diffusion" property the strategy depends on. The corpus relies on the *author* (or judgment-pair-reviewer agent under hand-review) for translation equivalence, not on an MT system.

**Split into separate `train.en.jsonl` + `train.ja.jsonl` files.** Considered. Argument for: deposit consumers can pick the file they want without filtering. Argument against: `meta.lang` already enables filtering trivially in any consumer language (one `jq` invocation), and splitting files multiplies the maintenance surface (separate validation runs per file, separate train/valid splits, etc.). The single-file `meta.lang`-tagged format is the lower-overhead choice.

## Consequences

### Immediate (structural)

- `corpus/v0.1.0/manifest.json` counts `by_lang` (334 EN + 517 JA = 851 total), exposing the language ratio so deposit readers can stratify their expectations.
- ADR-0004's Layer 2 rubric agent has a dedicated criterion (6: Bilingual Pair Equivalence) that confirms EN/JA pairs reach the same Decision.
- The extractor scripts (`extract_adrs.py`, `extract_glossary.py`, `extract_thesis.py`) read both the `.md` and `.ja.md` variants of each source and emit one pair per (source, lang) combination.
- The pilot pairs in `corpus/v0.1.0/pilot.jsonl` (Stage A) establish the precedent: 5 pairs covering both languages across two lines.

### Downstream

- A consumer doing RAG can filter by `meta.lang` against the user's query language at retrieval time.
- A consumer fine-tuning can decide per-language: EN-only (334 pairs), JA-only (517 pairs), both (851 pairs), or weighted blends. The `meta.lang` field is the only mechanism needed.
- A consumer doing ablation can measure whether language matters for a given downstream task by stratifying the corpus along `meta.lang`.
- Stage D's `eval/prompt_bank.yaml` follows the same convention: each evaluation prompt has both `en` and `ja` keys, and `eval_compare.py --lang en|ja|both` selects which to run. The bilingual structure is preserved end-to-end across the corpus and its eval suite.

### Risk

- **Drift between EN and JA pairs.** If a `judgment` pair's EN and JA forms reach materially different Decisions, the corpus encodes a contradiction. ADR-0004 Layer 2 rubric criterion 6 is the explicit guard. Hand-review per round (`CLAUDE.md` "Judgment generation protocol") catches what the rubric agent misses.
- **Cost.** Producing every judgment situation in two languages roughly doubles the per-pair authoring effort relative to a monolingual corpus. The Stage C judgment generation protocol absorbs this cost by running both languages inside the same Claude Code session (no extra API call), but the *attention* cost on the author is real and is the practical reason the v0.1.0 ratio is 334 EN / 517 JA rather than perfectly balanced.

## Lineage

- Parent line: `authorship-strategy/CLAUDE.md` LLM-mediated diffusion + bilingual property
- Companion invariants: ADR-0001 (corpus as primary artifact), ADR-0002 (Q&A shape)
- Companion validation: ADR-0004 Layer 2 rubric criterion 6 (Bilingual Pair Equivalence)
