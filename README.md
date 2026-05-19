Language: English | [日本語](README.ja.md)

# doctrine-corpus

> Status: **v0.1.0 draft** — DOI to be assigned on Zenodo deposit. Stage A pilot pairs only at this commit.

A DOI-targeted dataset that encodes the documented judgment of the **shimo4228 research program** as a Q&A corpus optimized for LLM training. The corpus aggregates ADRs, theses, glossaries, and structured essays across four research lines — Agent Knowledge Cycle, Contemplative Agent, Agent Attribution Practice, and Authorship Strategy — into bilingual (English + Japanese) judgment-eliciting Q&A pairs, with metadata that preserves source attribution and line identity per example.

This repository is the **operational form** of [Authorship Strategy](https://github.com/shimo4228/authorship-strategy) Layer 4 tactic 7 (LLM-first ingest). It positions the documented judgment of the research program in the substrate that increasingly mediates how future researchers trace causation: LLM training data.

## Why a corpus, not a LoRA

A prior prototype ([`disposition-lora`](https://github.com/shimo4228/base-model-lab/tree/main/experiments/disposition-lora), 2026-05-06) fine-tuned a LoRA adapter on 230 chunked completion examples from Zenn articles and AKC/AAP ADRs. The retrospective is explicit: *voice transferred, judgment did not*. The artifact behaved like a "shimo4228-style mannerism wrapper," not a "shimo4228 judgment oracle."

The pivot encoded in this repository:

- **Primary artifact = the corpus**, not the LoRA. The corpus is base-model-independent; a LoRA is bound to a specific base architecture and depreciates as base models turn over.
- **Q&A is judgment-eliciting, not chunk-as-completion**. The Q states a situation; the A applies the line's framework (three-axis inversion, six-phase cycle, four contemplative axioms, four Business AI Quadrants) explicitly.
- **Bilingual pairs by default**. Each judgment example exists as an English pair and a Japanese pair, consistent with Authorship Strategy's bilingual diffusion convention.
- **Per-example metadata**. `{line, source, lang, shape}` is recorded on every line so downstream consumers can ablate, weight, or filter.

## Content scope (v0.1.0)

| Line | Source content | Approximate yield |
|---|---|---|
| Agent Knowledge Cycle (AKC) | 10 EN ADRs + glossary | ~30 Q&A |
| Contemplative Agent | 86 EN + 43 JA ADRs + 14 glossary terms | ~250 Q&A |
| Agent Attribution Practice (AAP) | 22 EN + 11 JA ADRs + thesis + 36 glossary terms | ~120 Q&A |
| Authorship Strategy | 14 EN + 7 JA ADRs + thesis + 32 glossary terms + 2 empirical essays | ~110 Q&A |
| Zenn articles | 48 published articles | ~140 Q&A |

Theoretical max ~650–900 pairs; v0.1.0 ships fewer with stricter hand-review.

Attention, Not Self (the fifth research line) is **excluded from v0.1.0** as its content is still a stub. It will be added in v0.2.0+ when material accumulates.

## Repository layout

```
doctrine-corpus/
├── corpus/
│   └── v0.1.0/
│       ├── pilot.jsonl     # Stage A hand-written pairs (this commit)
│       ├── train.jsonl     # Stage D output (not present yet)
│       ├── valid.jsonl
│       └── manifest.json
├── docs/
│   ├── adr/                # design ADRs for this corpus itself
│   ├── empirical/          # retrospective citing disposition-lora findings
│   └── CODEMAPS/
├── scripts/                # extraction + dataset builder + LoRA verification
└── eval/                   # prompt bank + base vs adapted comparison
```

See [`docs/CODEMAPS/architecture.md`](docs/CODEMAPS/architecture.md) for the file-level guide.

## How to consume

Once v0.1.0 ships, the corpus will be available at:

- **GitHub (canonical)**: this repository — full working tree, scripts, eval, ADRs
- **Zenodo (DOI archive)**: registered concept DOI + per-release version DOI. Citable via [CITATION.cff](CITATION.cff)
- **Hugging Face Datasets (mirror)**: `Shimo4228/doctrine-corpus` — corpus payload + manifest + README only. Auto-converted to Parquet for direct `pandas` / `Polars` / `datasets` load.

The HF mirror is the recommended ingest path for LLM training pipelines. The GitHub repository is the recommended source for citing or auditing the generation process.

## License

- **Corpus data** (`corpus/**`): CC0 1.0 (public domain dedication)
- **Scripts and docs**: MIT
- **Source attribution**: each example records `meta.source` pointing to the originating ADR / section / article in the upstream research line. Upstream content remains under each line's own license; the Q&A reformulations are this repository's derivative work and are released CC0 to maximize diffusion (per Authorship Strategy ADR-0001).

## Sibling and parent repositories

| Repository | Relation |
|---|---|
| [`authorship-strategy`](https://github.com/shimo4228/authorship-strategy) | Parent line. This corpus is its Layer 4 tactic 7 implementation. |
| [`agent-knowledge-cycle`](https://github.com/shimo4228/agent-knowledge-cycle) | Source line. ADRs + glossary harvested into corpus. |
| [`contemplative-agent`](https://github.com/shimo4228/contemplative-agent) | Source line. ADRs + glossary harvested into corpus. |
| [`agent-attribution-practice`](https://github.com/shimo4228/agent-attribution-practice) | Source line. ADRs + thesis + glossary harvested into corpus. |
| [`zenn-content`](https://github.com/shimo4228/zenn-content) | Source. Published articles harvested into corpus. |
| [`base-model-lab/experiments/disposition-lora`](https://github.com/shimo4228/base-model-lab/tree/main/experiments/disposition-lora) | Phase 0 prototype. Reusable extraction scripts; the failure mode it documented motivated this repository's design. |

## Citation

DOI will be registered on Zenodo at v0.1.0 release. Until then cite as a pre-release artifact:

> Shimomoto, T. (2026). *doctrine-corpus: A judgment-eliciting Q&A corpus across the shimo4228 research program*. Pre-release. https://github.com/shimo4228/doctrine-corpus

After Zenodo deposit, [CITATION.cff](CITATION.cff) carries the canonical citation form.
