Language: English | [日本語](README.ja.md)

# doctrine-corpus

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337008.svg)](https://doi.org/10.5281/zenodo.20337008)

A DOI-targeted dataset that encodes the documented judgment of the **shimo4228 research program** as a Q&A corpus optimized for LLM training. The corpus aggregates ADRs, theses, glossaries, and structured essays across four research lines — Agent Knowledge Cycle, Contemplative Agent, Agent Attribution Practice, and Authorship Strategy — into bilingual (English + Japanese) judgment-eliciting Q&A pairs, with metadata that preserves source attribution and line identity per example.

This repository is the **operational form** of [Authorship Strategy](https://github.com/shimo4228/authorship-strategy) Layer 4 tactic 7 (LLM-first ingest). It positions the documented judgment of the research program in the substrate that increasingly mediates how future researchers trace causation: LLM training data.

## Why a corpus, not a LoRA

A prior prototype (`disposition-lora`, 2026-05-06; see [`docs/empirical/README.md`](docs/empirical/README.md) for the retrospective) fine-tuned a LoRA adapter on 230 chunked completion examples from Zenn articles and AKC/AAP ADRs. The retrospective is explicit: *voice transferred, judgment did not*. The artifact behaved like a "shimo4228-style mannerism wrapper," not a "shimo4228 judgment oracle."

The pivot encoded in this repository:

- **Primary artifact = the corpus**, not the LoRA. The corpus is base-model-independent; a LoRA is bound to a specific base architecture and depreciates as base models turn over. See [ADR-0001](docs/adr/0001-corpus-as-primary-artifact.md).
- **Q&A is judgment-eliciting, not chunk-as-completion**. The Q states a situation; the A applies the line's framework (three-axis inversion, six-phase cycle, four contemplative axioms, four Business AI Quadrants) explicitly.
- **Bilingual pairs by default**. Each judgment example exists as an English pair and a Japanese pair, consistent with Authorship Strategy's bilingual diffusion convention.
- **Per-example metadata**. `{line, source, lang, shape}` is recorded on every line so downstream consumers can ablate, weight, or filter.

## Intended uses and current limitations

The corpus is designed to be used as an **ingredient**, not as a standalone fine-tuning package.

**Verified for:**
- **RAG retrieval material** — bilingual judgment Q&A pairs work well as retrieved context for downstream LLM applications.
- **Mixing into larger instruction-tuning corpora** — 851 examples is a small but high-density addition to FLAN/Alpaca-scale mixes.
- **Human reading material** — the corpus is designed to be readable end-to-end as a reference text for the research program's judgment patterns.

**Not yet verified:**
- **Standalone small-LoRA fine-tuning.** A Stage D verification LoRA (Qwen3-8B-4bit, 300 iter on 851 examples) was trained as a disposable probe and reproduced the same "mannerism wrapper" failure mode as the Phase 0 prototype — voice transferred, judgment did not. The corpus is base-model-independent and is retained as the deliverable; the LoRA was never a deposit target. See [ADR-0005](docs/adr/0005-stage-d-verification-lora-result.md) for the verdict and v0.2.0 hypotheses (data scale, shape distribution, base model effect).

## Content scope (v0.1.0)

851 examples in total, distributed across the four research lines and one source of published articles:

| Line | Examples |
|---|---:|
| Agent Knowledge Cycle (AKC) | 38 |
| Contemplative Agent | 318 |
| Agent Attribution Practice (AAP) | 146 |
| Authorship Strategy | 126 |
| Zenn articles | 222 |
| Cross-line (`shape: contrast`) | 1 |
| **Total** | **851** |

By language: 334 English / 517 Japanese.
By shape: 343 judgment / 371 explain / 136 definition / 1 contrast.

The train/valid split is 766/85 (seed=42, val-fraction=0.1).

Attention, Not Self (the fifth research line) is **excluded from v0.1.0** as its content is still a stub. It will be added in v0.2.0+ when material accumulates.

## Repository layout

```
doctrine-corpus/
├── corpus/
│   └── v0.1.0/
│       ├── pilot.jsonl     # 5 hand-written precedent pairs
│       ├── train.jsonl     # 766 examples (seed=42)
│       ├── valid.jsonl     # 85 examples (seed=42)
│       └── manifest.json   # version, counts, source commits, verification verdict
├── docs/
│   ├── adr/                # design ADRs (0001..0005)
│   ├── empirical/          # Phase 0 retrospective (disposition-lora findings)
│   └── CODEMAPS/
├── scripts/                # extraction + dataset builder + LoRA verification
└── eval/                   # prompt bank + base vs adapted comparison
```

See [`docs/CODEMAPS/architecture.md`](docs/CODEMAPS/architecture.md) for the file-level guide.

## How to consume

The corpus is distributed via:

- **GitHub (canonical)**: this repository — full working tree, scripts, eval, ADRs.
- **Zenodo (DOI archive)**: concept DOI + per-release version DOI. Citable via [CITATION.cff](CITATION.cff).
- **Hugging Face Datasets (mirror)**: `Shimo4228/doctrine-corpus` — corpus payload + manifest + README only. Auto-converted to Parquet for direct `pandas` / `Polars` / `datasets` load.

The HF mirror is the recommended ingest path for LLM training pipelines and RAG ingestion. The GitHub repository is the recommended source for citing or auditing the generation process.

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
| `base-model-lab/experiments/disposition-lora` (private) | Phase 0 prototype. Reusable extraction scripts; the failure mode it documented motivated this repository's design. See [`docs/empirical/README.md`](docs/empirical/README.md) for the retrospective. |

## Citation

Cite using the **concept DOI** (which always resolves to the latest version): [10.5281/zenodo.20337008](https://doi.org/10.5281/zenodo.20337008). The canonical citation form is in [CITATION.cff](CITATION.cff).

Reference shape:

> Shimomoto, T. (2026). *doctrine-corpus: A judgment-eliciting Q&A corpus across the shimo4228 research program*. Zenodo. https://doi.org/10.5281/zenodo.20337008

For reproducibility citation of a specific historical version, use the v0.1.0 version DOI: [10.5281/zenodo.20337009](https://doi.org/10.5281/zenodo.20337009).
