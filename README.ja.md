言語: [English](README.md) | 日本語

# doctrine-corpus

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20337008.svg)](https://doi.org/10.5281/zenodo.20337008) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/shimo4228/doctrine-corpus)

著者（shimo4228）が書き残した設計上の判断を、問いと答えの組（Q&A）にした DOI 登録済みのデータセットです。LLM の学習用データの混合や RAG の索引を作る人と、その判断の筋道を読みたい人に向けています。1 例は chat message 形式の Q&A 1 件で、英語か日本語で書かれ、どのプロジェクトのどの文書から来たかをメタデータとして記録しています。出典は、著者の 4 つの長期プロジェクト（それぞれ単独で引用できます。Agent Knowledge Cycle / Contemplative Agent / Agent Attribution Practice / Authorship Strategy）の設計判断の記録（ADR）・主張をまとめた文書・用語集・構造化されたエッセイと、著者が Zenn に公開した記事の節（222 例）です。

著者の [Authorship Strategy](https://github.com/shimo4228/authorship-strategy) プロジェクトにある戦術の一つ、著者の仕事を LLM が学ぶ場所に置くことを実際に行うものです。

`judgment` の例を 1 件示します。Agent Knowledge Cycle の ADR から LLM が生成した英語の例で（`meta.source: docs/adr/0004-two-stage-distill-pipeline.md#decision`）、答えは短く切っています。

> **Q:** Why not just put the JSON schema directly in the system prompt of a single distillation call and have the model produce both insight and structure in one pass? It saves an LLM round-trip.
>
> **A:** The round-trip is what the design is buying. A single-stage call with a schema in the system prompt forces the model to satisfy format and reason about the episodes in the same forward pass; the schema wins and the patterns come out shallow [...] The extra call is the price of giving each stage a clean reasoning budget.

## なぜ LoRA ではなくコーパスか

先行する試作の `disposition-lora`（2026-05-06、振り返りは [`docs/empirical/README.md`](docs/empirical/README.md)（英語）を参照）では、Zenn 記事と AKC/AAP の ADR から、文章の断片の続きを書かせる形（chunked completion）の例を 230 件作り、LoRA adapter を学習させました。振り返りがはっきり書いているとおり、*文体は移りましたが、判断は移りませんでした*。できたものは「shimo4228 風の口癖をまとうだけのもの（mannerism wrapper）」になり、「shimo4228 の判断を答えるもの（judgment oracle）」にはなりませんでした。

このリポジトリでは、設計を次のように切り替えました。

- **主な成果物はコーパス** で、LoRA ではありません。コーパスは土台のモデル（base model）に依存しません。LoRA は特定のモデル構造に縛られ、土台のモデルの世代交代で価値が下がります。詳細は [ADR-0001](docs/adr/0001-corpus-as-primary-artifact.md)（英語）を参照してください
- **`judgment` の 343 例は判断を引き出す形（judgment-eliciting）** で、出典の文章の続きを書くようにモデルを訓練する形（chunk-as-completion）ではありません。Q は状況を示し、A は決定に至ります。作り方は 3 通りです。LLM が生成した 226 件では、A は出典のプロジェクト自身の枠組みをはっきり当てはめます。ADR からスクリプトで抽出した 113 件では、Q が ADR の Context を状況として示し、A は ADR 自身の Decision の本文です。残りの 4 件は手で書いた pilot の組です。それ以外の例の多くは、そのまま説明する形です。`explain` の例は ADR や主張の節を、`definition` の例は用語集の項目を述べ直したもので、Zenn の 222 例は試作と同じ形のまま、Q が記事の 1 節を書くよう求め、A がその節の本文になっています
- **原文が英日両方あるときは英日の組にします**。出典が英日両方にある場合、各 judgment の例を英語と日本語で 1 件ずつ置きます。これは Authorship Strategy の英日両言語で広める規約に従っています。v0.1.0 の judgment の例は英語 188 / 日本語 155 です。Agent Attribution Practice と Authorship Strategy はすべて組になっています。Contemplative Agent は 120 / 114 で、v0.1.0 を作った時点で出典の ADR のうち 2 件に日本語版がまだなかったためです。Agent Knowledge Cycle はほぼ英語だけ（28 / 1）で、その ADR に日本語版がないためです（日本語の 1 件は手で書いた pilot の組です）
- **例ごとのメタデータ**。`{line, source, lang, shape}` を各行に記録し、下流の利用者が特定の出典を外したり、重みを変えたり、絞り込んだりできるようにしています。`shape` は例の形で、`judgment`、`explain`（説明）、`definition`（用語集の項目）、`contrast`（1 つの状況で 2 つのプロジェクトがどう違うか）のどれかです

## 想定される用途と現時点での制約

このコーパスは、ほかのデータに混ぜる **素材（ingredient）** として使うことを想定しており、単独の追加学習（fine-tuning）用のパッケージとしては設計していません。

**想定している用途**（そのように設計していますが、どれもまだ試していません。[ADR-0001](docs/adr/0001-corpus-as-primary-artifact.md)（英語）を参照）:
- **RAG で取り出す資料**: 英日の judgment の Q&A を、下流の LLM アプリケーションが取り出す文脈として使います
- **指示への応答を学習させる大規模データ（instruction-tuning）への混入**: 851 例は、FLAN / Alpaca 規模の混合データに足す小さな追加です
- **人が読む参照資料**: 著者の判断のパターンを知る参照テキストとして、最初から最後まで読めるように作っています

**試して失敗した用途:**
- **単独の小規模 LoRA 学習。** 使い捨ての検証用 LoRA（Qwen3-8B-4bit、851 例 × 300 iter）を学習させたところ、判定は FAIL でした。`disposition-lora` の試作と同じ「口癖をまとうだけ（mannerism wrapper）」の失敗を再現し、文体は移りましたが、判断は移りませんでした。詳細と、そこに記録した v0.2.0 の 2 つの仮説（データの規模、shape の配分）は [ADR-0005](docs/adr/0005-stage-d-verification-lora-result.md)（英語）を参照してください。より大きな土台のモデルを試すことは、同じ ADR で対象外としています

## 収録範囲（v0.1.0）

合計 851 例で、4 つの長期プロジェクトと、公開済みの記事という 1 つの出典に分かれています。

| 長期プロジェクト | 例の数 |
|---|---:|
| Agent Knowledge Cycle (AKC) | 38 |
| Contemplative Agent | 318 |
| Agent Attribution Practice (AAP) | 146 |
| Authorship Strategy | 126 |
| Zenn の記事 | 222 |
| Cross-line (`shape: contrast`) | 1 |
| **合計** | **851** |

言語別は英語 334 / 日本語 517 です（Zenn の 222 例はすべて日本語です）。
Shape 別は judgment 343 / explain 371 / definition 136 / contrast 1 です。

例の作り方: pilot の 5 件は手で書き（judgment 4、contrast 1）、judgment の 226 件は Claude Code のセッションの中で LLM が生成し、残りの 620 例は出典の文書からスクリプトで抽出しました。抽出の内訳は、ADR から 238 例（judgment 113、explain 125）、Zenn の記事から 222 例（explain）、用語集から 136 例（definition）、主張をまとめた文書から 24 例（explain）です。出典ごとの件数は [`manifest.json`](corpus/v0.1.0/manifest.json) にあります。

train/valid の分割は 766/85（seed=42、val-fraction=0.1）です。pilot の 5 件はこの 851 例にすでに含まれているので、`pilot.jsonl` を重ねて足さないでください。

5 つ目の長期プロジェクトである Attention, Not Self は、v0.1.0 の公開時（2026-05-22）に内容がまだ書きかけ（stub）の段階だったので **v0.1.0 では対象外** です。v0.2.0 以降で追加する予定です。

## リポジトリの構成

```
doctrine-corpus/
├── corpus/
│   └── v0.1.0/
│       ├── pilot.jsonl     # 手書きの先例の組 5 件（train/valid にも含む）
│       ├── train.jsonl     # 766 例 (seed=42)
│       ├── valid.jsonl     # 85 例 (seed=42)
│       └── manifest.json   # 版、件数、出典の commit、検証の判定
├── docs/
│   ├── adr/                # 設計の ADR (0001..0005)
│   ├── empirical/          # disposition-lora 試作の振り返り
│   └── CODEMAPS/
├── scripts/                # 抽出、データセットの組み立て、LoRA の検証
└── eval/                   # プロンプト集と、土台のモデルと適応後のモデルの比較
```

ファイルごとの案内は [`docs/CODEMAPS/architecture.md`](docs/CODEMAPS/architecture.md)（英語）にあります。

## 利用方法

このコーパスは次の経路で配布しています。

- **GitHub（正本）**: このリポジトリ。作業ツリー全体、scripts、eval、ADR があります
- **Zenodo（DOI archive）**: concept DOI とリリースごとの version DOI。どちらで引用するかは [引用](#引用) にあります
- **Hugging Face Datasets（ミラー）**: [`Shimo4228/doctrine-corpus`](https://huggingface.co/datasets/Shimo4228/doctrine-corpus)。コーパスのファイルと manifest に加えて、引用のメタデータ、変更履歴、AI 向けのファイル（llms.txt、graph.jsonld）と、この README とは別に整えたデータセットの説明（dataset card）を置いています。scripts、eval、ADR は置いていません。Parquet に自動変換され、`pandas` / `Polars` / `datasets` から直接読み込めます

LLM の学習パイプラインや RAG に取り込むなら HF のミラーをおすすめします。生成過程の監査には GitHub のリポジトリをおすすめします。

HF のミラーから読み込むと `train`、`validation`、`pilot` の split が得られます。`validation` は `valid.jsonl` にあたり、`pilot` の 5 件は、ほかの 2 つにすでに入っています。

```bash
pip install datasets
python -c "from datasets import load_dataset; print(load_dataset('Shimo4228/doctrine-corpus'))"
```

データを最小限のぞくだけなら git だけで足ります。split の各行が、`meta` 付きの Q&A の例 1 件です。

```bash
git clone https://github.com/shimo4228/doctrine-corpus
head -n 1 doctrine-corpus/corpus/v0.1.0/train.jsonl
```

## 引用

引用には、常に最新版へつながる **concept DOI** [10.5281/zenodo.20337008](https://doi.org/10.5281/zenodo.20337008) を使ってください。完全なメタデータは [CITATION.cff](CITATION.cff) と [`codemeta.json`](codemeta.json)（schema.org に基づくデータセットのメタデータで、Software Heritage の索引作成ツールが読みます）にあります。どちらも concept DOI ではなく v0.1.0 の version DOI を載せています。

引用の形:

> Shimomoto, T. (2026). *doctrine-corpus: A judgment-eliciting Q&A corpus across the shimo4228 research program*. Zenodo. https://doi.org/10.5281/zenodo.20337008

特定の版を再現のために引用するときは、v0.1.0 の version DOI [10.5281/zenodo.20337009](https://doi.org/10.5281/zenodo.20337009) を使ってください。

## 著者のほかの仕事

- **[authorship-strategy](https://github.com/shimo4228/authorship-strategy)**: 親の長期プロジェクトです。著者がそもそもなぜ自分の判断を CC0 の学習データとして公開するのか（作品を開いて、拡散に起点を運ばせる）が分かります。
- **[agent-knowledge-cycle](https://github.com/shimo4228/agent-knowledge-cycle)**: 出典の長期プロジェクトの一つです。coding agent の経験を skill と rule に変える 6 段階の循環で、`akc` の例はこれを当てはめています。
- **[contemplative-agent](https://github.com/shimo4228/contemplative-agent)**: いちばん大きい出典の長期プロジェクト（318 例）です。ローカル LLM で長く動き、人の承認のもとで自分の憲法（constitution）の変更を提案するエージェントの ADR があります。
- **[agent-attribution-practice](https://github.com/shimo4228/agent-attribution-practice)**: 自律エージェントが失敗したとき誰が答えるかを扱う出典の長期プロジェクトです。`aap` の例は、その 4 つの Business AI Quadrants を当てはめています。これは、仕事が決定的に処理できるか意味の判断を要するか、手順が決まっているか探索的かで、仕事の振り分け先を決める枠組みです。
- **[shimo4228](https://github.com/shimo4228/shimo4228)**: 著者の hub です。5 つの長期プロジェクト（それぞれ単独で引用できます）とその DOI がまとまっていて、このコーパスはそのうち 4 つを出典にしています。

## ライセンス

- **コーパスのデータ**（`corpus/**`）: CC0 1.0（public domain dedication）。[`LICENSE`](LICENSE) にあります
- **スクリプト**（`scripts/**`）**と docs**: MIT。[`scripts/LICENSE`](scripts/LICENSE) にあります
- **出典の記録**: 各例の `meta.source` に、上流の長期プロジェクトの出典（ADR / 節 / 記事）を記録しています。上流の内容はそれぞれのプロジェクトのライセンスに従います。Q&A への書き直しはこのリポジトリの派生物で、拡散を最大にするため CC0 で公開しています（Authorship Strategy の ADR-0015、読み手に応じたライセンスの選択に従います）

<details>
<summary>ツールと AI アシスタント向けの資料</summary>

doctrine-corpus は、著者の長期プロジェクトに記録された判断を英語と日本語の Q&A の組にした CC0 のデータセットで、LLM の学習用データの混合や RAG の索引を作る人、その判断を参照として読みたい人に向けて公開しています。

これがあるのは、記事の本文を切り出して学習させた先行の LoRA の試作が、著者の文体は移したのに判断を移さなかったからです。このリポジトリは代わりにコーパスを主な成果物にしました。judgment の 343 例では Q が状況を示し、A が決定に至ります（LLM が生成した 226 件の A は出典のプロジェクトの枠組みを当てはめ、ADR から抽出した 113 件の A は ADR 自身の Decision の本文です）。コーパス全体は、土台のモデルが変わっても使えます。著者の仕事を LLM が学ぶ場所に置く戦術である LLM-first ingest（[Authorship Strategy](https://github.com/shimo4228/authorship-strategy) の Layer 4、tactic 7、concept DOI 10.5281/zenodo.20263316）を実際に行ったものです。

基本的な事実: 著者は Tatsuya Shimomoto です。コーパスのデータは CC0 1.0、scripts と docs は MIT です。形式は chat message 形式の JSONL で、すべての例に `meta.{line, source, lang, shape}` があります。抽出の scripts には Python 3.11 以上が要り、LoRA の検証をやり直すにはさらに Apple Silicon の Mac と `train` の extra（mlx-lm）が要ります。有料の鍵は要りません（LLM が生成した judgment の 226 件は、API ではなく Claude Code のセッションの中で生成しました）。状態: 手で整えています。v0.1.0 は 2026-05-22 に公開した変更しないスナップショット で、v0.2.0 では Attention, Not Self を加え、ADR-0005 の 2 つの仮説を検証の対象にする予定です。5 件は手で書き、judgment の 226 件は Claude Code のセッションの中で LLM が生成し、残りの 620 件はスクリプトで抽出しました。出典は agent-knowledge-cycle、contemplative-agent、agent-attribution-practice、authorship-strategy の各リポジトリと、[zenn-content](https://github.com/shimo4228/zenn-content) の記事の原稿です。引用には concept DOI [10.5281/zenodo.20337008](https://doi.org/10.5281/zenodo.20337008) を使い、v0.1.0 の version DOI は 10.5281/zenodo.20337009 です。完全なメタデータは CITATION.cff と codemeta.json にあります。

核になる語: **judgment-eliciting** な組は、ある状況でどう決めるかを問い、枠組みを当てはめて答えます。これに対し **chunk-as-completion** は、出典の文章の続きを書くようにモデルを訓練します。**shape** は `judgment`、`explain`、`definition`、`contrast` のどれかです。**line** は出典のプロジェクト（`akc`、`contemplative-agent`、`aap`、`authorship-strategy`、`zenn`、`cross-line`）です。

例: v0.1.0 は 851 例（英語 334 / 日本語 517、judgment 343 / explain 371 / definition 136 / contrast 1）で、seed 42 で train 766 / valid 85 に分けています。これで訓練した検証用の LoRA（Qwen3-8B-4bit、300 iter）は以前の失敗を再現し、文体は移っても判断は移りませんでした。そのためコーパスは、単独の追加学習（fine-tuning）用のパッケージとしてではなく、RAG や、指示への応答を学習させる大規模データ（instruction-tuning）に混ぜる素材として提供しています。

リンク: [llms.txt](llms.txt)、[llms-full.txt](llms-full.txt)、[graph.jsonld](graph.jsonld)、[corpus/README.md](corpus/README.md)（schema、英語）、[docs/adr/](docs/adr/)（設計判断、検証の結果は ADR-0005、英語）、[docs/empirical/README.md](docs/empirical/README.md)（試作の振り返り、英語）、Hugging Face のミラー [Shimo4228/doctrine-corpus](https://huggingface.co/datasets/Shimo4228/doctrine-corpus)。

</details>
