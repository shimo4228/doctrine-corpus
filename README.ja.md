言語: [English](README.md) | 日本語

# doctrine-corpus

> Status: **v0.1.0 draft** — DOI は Zenodo deposit 時に採番される。現コミットは Stage A pilot pair のみを含む。

**shimo4228 研究プログラム**の documented judgment を、LLM training 用に最適化された Q&A corpus として encode する DOI 取得予定の dataset。Agent Knowledge Cycle / Contemplative Agent / Agent Attribution Practice / Authorship Strategy の 4 research line に渡る ADR・thesis・glossary・structured essay を集約し、英語 + 日本語の bilingual な judgment-eliciting Q&A pair に変換する。各 example には source attribution と line 識別子が metadata として保持される。

本 repo は [Authorship Strategy](https://github.com/shimo4228/authorship-strategy) Layer 4 tactic 7 (LLM-first ingest) の **operational form** である。研究プログラムの documented judgment を、将来の研究者が causation を辿る経路を mediate する基盤 = LLM training data に配置する。

## なぜ LoRA ではなく corpus か

先行する prototype [`disposition-lora`](https://github.com/shimo4228/base-model-lab/tree/main/experiments/disposition-lora) (2026-05-06) で Zenn 記事と AKC/AAP ADR から 230 件 chunked completion 例を作り LoRA adapter を fine-tune した。retrospective が明示する通り、*voice は transfer したが judgment は transfer しなかった*。Artifact は「shimo4228 風 mannerism wrapper」になり、「shimo4228 judgment oracle」にはならなかった。

本 repo の design 上の pivot:

- **Primary artifact = corpus**、LoRA ではない。Corpus は base model 非依存。LoRA は特定 base architecture に縛られ、base model 世代交代で減価する
- **Q&A は judgment-eliciting**、chunk-as-completion ではない。Q は状況を提示し、A はその line の framework (3 軸反転、6 phase cycle、4 contemplative axioms、4 Business AI Quadrants) を明示的に適用する
- **Bilingual pair が default**。各 judgment example は英語 pair + 日本語 pair として併存する。Authorship Strategy の bilingual diffusion 規約に従う
- **Per-example metadata**。`{line, source, lang, shape}` を各行に記録し、downstream consumer による ablation / weighting / filtering を可能にする

## Content scope (v0.1.0)

| Line | Source content | Approximate yield |
|---|---|---|
| Agent Knowledge Cycle (AKC) | 10 EN ADR + glossary | 約 30 Q&A |
| Contemplative Agent | 86 EN + 43 JA ADR + glossary 14 terms | 約 250 Q&A |
| Agent Attribution Practice (AAP) | 22 EN + 11 JA ADR + thesis + glossary 36 terms | 約 120 Q&A |
| Authorship Strategy | 14 EN + 7 JA ADR + thesis + glossary 32 terms + empirical 2 essay | 約 110 Q&A |
| Zenn articles | 48 published 記事 | 約 140 Q&A |

理論上限 約 650–900 pair。v0.1.0 はより厳しい hand-review のもとで少なめに ship する。

5 つ目の line である Attention, Not Self は内容が stub 段階のため **v0.1.0 では対象外**。素材が貯まる v0.2.0+ で追加する。

## Repository layout

```
doctrine-corpus/
├── corpus/
│   └── v0.1.0/
│       ├── pilot.jsonl     # Stage A 手書き pair (本コミット)
│       ├── train.jsonl     # Stage D 出力 (本コミットでは未生成)
│       ├── valid.jsonl
│       └── manifest.json
├── docs/
│   ├── adr/                # 本 corpus 自身の design ADR
│   ├── empirical/          # disposition-lora findings を引用する retrospective
│   └── CODEMAPS/
├── scripts/                # extraction + dataset builder + LoRA verification
└── eval/                   # prompt bank + base vs adapted comparison
```

ファイルレベルの案内は [`docs/CODEMAPS/architecture.md`](docs/CODEMAPS/architecture.md) を参照。

## 利用方法

v0.1.0 ship 後、本 corpus は以下から取得できる:

- **GitHub (canonical)**: 本 repo — full working tree、scripts、eval、ADR
- **Zenodo (DOI archive)**: concept DOI + per-release version DOI。[CITATION.cff](CITATION.cff) 経由で citable
- **Hugging Face Datasets (mirror)**: `Shimo4228/doctrine-corpus` — corpus payload + manifest + README のみ。Parquet 自動変換が走り `pandas` / `Polars` / `datasets` から直接 load 可能

LLM training pipeline からの ingest path は HF mirror が推奨。生成 process の audit / citation には GitHub repo が推奨。

## License

- **Corpus data** (`corpus/**`): CC0 1.0 (public domain dedication)
- **Scripts and docs**: MIT
- **Source attribution**: 各 example の `meta.source` field に upstream research line の出典 ADR / section / article が記録される。Upstream content は各 line の license に従い、Q&A への reformulation は本 repo の derivative work であり、diffusion を最大化するため CC0 で release する (Authorship Strategy ADR-0001 に従う)

## Sibling および parent repository

| Repository | Relation |
|---|---|
| [`authorship-strategy`](https://github.com/shimo4228/authorship-strategy) | Parent line。本 corpus はその Layer 4 tactic 7 implementation |
| [`agent-knowledge-cycle`](https://github.com/shimo4228/agent-knowledge-cycle) | Source line。ADR + glossary を corpus に harvest |
| [`contemplative-agent`](https://github.com/shimo4228/contemplative-agent) | Source line。ADR + glossary を corpus に harvest |
| [`agent-attribution-practice`](https://github.com/shimo4228/agent-attribution-practice) | Source line。ADR + thesis + glossary を corpus に harvest |
| [`zenn-content`](https://github.com/shimo4228/zenn-content) | Source。Published 記事を corpus に harvest |
| [`base-model-lab/experiments/disposition-lora`](https://github.com/shimo4228/base-model-lab/tree/main/experiments/disposition-lora) | Phase 0 prototype。Extraction script の流用元、かつ documented 失敗 mode が本 repo の design を motivate した |

## Citation

DOI は v0.1.0 release 時に Zenodo で採番される。それまでは pre-release artifact として:

> Shimomoto, T. (2026). *doctrine-corpus: A judgment-eliciting Q&A corpus across the shimo4228 research program*. Pre-release. https://github.com/shimo4228/doctrine-corpus

Zenodo deposit 後は [CITATION.cff](CITATION.cff) が canonical citation form を保持する。
