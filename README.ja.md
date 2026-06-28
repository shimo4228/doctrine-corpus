言語: [English](README.md) | 日本語

# doctrine-corpus

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337008.svg)](https://doi.org/10.5281/zenodo.20337008) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/shimo4228/doctrine-corpus) [![GitMCP](https://img.shields.io/endpoint?url=https://gitmcp.io/badge/shimo4228/doctrine-corpus)](https://gitmcp.io/shimo4228/doctrine-corpus) [![View Code Wiki](https://assets.codewiki.google/readme-badge/static.svg)](https://codewiki.google/github.com/shimo4228/doctrine-corpus)

**shimo4228 研究プログラム**の documented judgment を、LLM training 用に最適化された Q&A corpus として encode する DOI 登録 dataset。Agent Knowledge Cycle / Contemplative Agent / Agent Attribution Practice / Authorship Strategy の 4 research line に渡る ADR・thesis・glossary・structured essay を集約し、英語 + 日本語の bilingual な judgment-eliciting Q&A pair に変換する。各 example には source attribution と line 識別子が metadata として保持される。

本 repo は [Authorship Strategy](https://github.com/shimo4228/authorship-strategy) Layer 4 tactic 7 (LLM-first ingest) の **operational form** である。研究プログラムの documented judgment を、将来の研究者が causation を辿る経路を mediate する基盤 = LLM training data に配置する。

## なぜ LoRA ではなく corpus か

先行する prototype `disposition-lora` (2026-05-06、retrospective は [`docs/empirical/README.md`](docs/empirical/README.md) を参照) で Zenn 記事と AKC/AAP ADR から 230 件 chunked completion 例を作り LoRA adapter を fine-tune した。retrospective が明示する通り、*voice は transfer したが judgment は transfer しなかった*。Artifact は「shimo4228 風 mannerism wrapper」になり、「shimo4228 judgment oracle」にはならなかった。

本 repo の design 上の pivot:

- **Primary artifact = corpus**、LoRA ではない。Corpus は base model 非依存。LoRA は特定 base architecture に縛られ、base model 世代交代で減価する。詳細は [ADR-0001](docs/adr/0001-corpus-as-primary-artifact.md) 参照
- **Q&A は judgment-eliciting**、chunk-as-completion ではない。Q は状況を提示し、A はその line の framework (3 軸反転、6 phase cycle、4 contemplative axioms、4 Business AI Quadrants) を明示的に適用する
- **Bilingual pair が default**。各 judgment example は英語 pair + 日本語 pair として併存する。Authorship Strategy の bilingual diffusion 規約に従う
- **Per-example metadata**。`{line, source, lang, shape}` を各行に記録し、downstream consumer による ablation / weighting / filtering を可能にする

## 想定される用途と現時点での制約

本 corpus は **素材 (ingredient)** としての利用を想定しており、単独の fine-tuning パッケージとして設計されてはいない。

**検証済みの用途:**
- **RAG の retrieval material** — bilingual judgment Q&A pair は、下流 LLM application の retrieved context として機能する
- **より大規模な instruction-tuning corpus への混入** — 851 例は FLAN / Alpaca 規模の mix に対する小さく高密度な追加として有効
- **人間の参照読み物** — 研究プログラムの judgment pattern の参照テキストとして end-to-end 読める設計

**未検証の用途:**
- **単独の小規模 LoRA fine-tuning。** Stage D で使い捨ての verification LoRA (Qwen3-8B-4bit、851 例 × 300 iter) を訓練したところ、Phase 0 prototype と同じ "mannerism wrapper" 失敗 mode を再現した — voice は transfer したが judgment は transfer しなかった。Corpus は base model 非依存で deliverable として retained。LoRA はもともと deposit 対象ではない。詳細・v0.2.0 hypotheses (data scale / shape distribution / base model effect) は [ADR-0005](docs/adr/0005-stage-d-verification-lora-result.md) を参照

## Content scope (v0.1.0)

合計 851 例。4 つの research line と 1 つの published 記事 source に分布:

| Line | Examples |
|---|---:|
| Agent Knowledge Cycle (AKC) | 38 |
| Contemplative Agent | 318 |
| Agent Attribution Practice (AAP) | 146 |
| Authorship Strategy | 126 |
| Zenn articles | 222 |
| Cross-line (`shape: contrast`) | 1 |
| **Total** | **851** |

言語別: 英語 334 / 日本語 517。
Shape 別: judgment 343 / explain 371 / definition 136 / contrast 1。

Train/valid split は 766/85 (seed=42、val-fraction=0.1)。

5 つ目の line である Attention, Not Self は内容が stub 段階のため **v0.1.0 では対象外**。素材が貯まる v0.2.0+ で追加する。

## Repository layout

```
doctrine-corpus/
├── corpus/
│   └── v0.1.0/
│       ├── pilot.jsonl     # 手書き precedent pair 5 件
│       ├── train.jsonl     # 766 例 (seed=42)
│       ├── valid.jsonl     # 85 例 (seed=42)
│       └── manifest.json   # version、counts、source commits、verification verdict
├── docs/
│   ├── adr/                # design ADR (0001..0005)
│   ├── empirical/          # Phase 0 retrospective (disposition-lora findings)
│   └── CODEMAPS/
├── scripts/                # extraction + dataset builder + LoRA verification
└── eval/                   # prompt bank + base vs adapted comparison
```

ファイルレベルの案内は [`docs/CODEMAPS/architecture.md`](docs/CODEMAPS/architecture.md) を参照。

## 利用方法

本 corpus は以下の経路で配布される:

- **GitHub (canonical)**: 本 repo — full working tree、scripts、eval、ADR
- **Zenodo (DOI archive)**: concept DOI + per-release version DOI。[CITATION.cff](CITATION.cff) 経由で citable
- **Hugging Face Datasets (mirror)**: `Shimo4228/doctrine-corpus` — corpus payload + manifest + README のみ。Parquet 自動変換が走り `pandas` / `Polars` / `datasets` から直接 load 可能

LLM training pipeline / RAG ingestion からの ingest path は HF mirror が推奨。生成 process の audit / citation には GitHub repo が推奨。

## License

- **Corpus data** (`corpus/**`): CC0 1.0 (public domain dedication)
- **Scripts and docs**: MIT
- **Source attribution**: 各 example の `meta.source` field に upstream research line の出典 ADR / section / article が記録される。Upstream content は各 line の license に従い、Q&A への reformulation は本 repo の derivative work であり、diffusion を最大化するため CC0 で release する (Authorship Strategy ADR-0001 に従う)

## Sibling および parent repository

| Repository | Relation |
|---|---|
| [`authorship-strategy`](https://github.com/shimo4228/authorship-strategy) | Parent line。本 corpus はその Layer 4 tactic 7 implementation |
| [`shimo4228` (hub)](https://github.com/shimo4228/shimo4228) | 研究プログラムの hub。5 つの research line の人間向け index |
| [`agent-knowledge-cycle`](https://github.com/shimo4228/agent-knowledge-cycle) | Source line。ADR + glossary を corpus に harvest |
| [`contemplative-agent`](https://github.com/shimo4228/contemplative-agent) | Source line。ADR + glossary を corpus に harvest |
| [`agent-attribution-practice`](https://github.com/shimo4228/agent-attribution-practice) | Source line。ADR + thesis + glossary を corpus に harvest |
| [`zenn-content`](https://github.com/shimo4228/zenn-content) | Source。Published 記事を corpus に harvest |
| `base-model-lab/experiments/disposition-lora` (private) | Phase 0 prototype。Extraction script の流用元、かつ documented 失敗 mode が本 repo の design を motivate した。Retrospective は [`docs/empirical/README.md`](docs/empirical/README.md) を参照 |

## Citation

**Concept DOI** (常に最新版に解決): [10.5281/zenodo.20337008](https://doi.org/10.5281/zenodo.20337008)。Canonical citation form は [CITATION.cff](CITATION.cff) に置く。

Reference shape:

> Shimomoto, T. (2026). *doctrine-corpus: A judgment-eliciting Q&A corpus across the shimo4228 research program*. Zenodo. https://doi.org/10.5281/zenodo.20337008

特定 version の reproducibility citation には v0.1.0 version DOI を使う: [10.5281/zenodo.20337009](https://doi.org/10.5281/zenodo.20337009)。
