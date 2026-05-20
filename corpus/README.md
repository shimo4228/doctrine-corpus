# Corpus

The actual dataset payload. Each `vX.Y.Z/` subdirectory is an immutable snapshot indexed by its Zenodo version DOI.

## Schema

One JSONL line per example. Format:

```json
{
  "messages": [
    {"role": "user", "content": "Q text"},
    {"role": "assistant", "content": "A text"}
  ],
  "meta": {
    "line": "authorship-strategy",
    "source": "docs/thesis.md#three-axis-inversion",
    "lang": "en",
    "shape": "judgment"
  }
}
```

`messages` follows the chat-completion format consumed by `mlx-lm lora` and by most instruction-tuning frameworks. `meta` is consumed by downstream filters / ablations and is silently ignored by the trainer.

### `meta.line`

The originating research line. Allowed values:

| value | source repo |
|---|---|
| `akc` | shimo4228/agent-knowledge-cycle |
| `contemplative-agent` | shimo4228/contemplative-agent |
| `aap` | shimo4228/agent-attribution-practice |
| `authorship-strategy` | shimo4228/authorship-strategy |
| `zenn` | shimo4228/zenn-content |
| `cross-line` | reserved for `shape: contrast` examples that cite multiple lines |

### `meta.source`

A repo-relative pointer to the originating content within the source line. For ADRs and structured docs this is a path + optional fragment (`docs/adr/0009-akc-is-a-cycle-not-a-harness.md#decision`). For Zenn articles this is the article slug.

`meta.source` does **not** include a base URL or repo URL; the line is identifiable from `meta.line` and the path is relative to that line's repo root. This keeps the corpus stable across upstream repo URL changes.

### `meta.lang`

`en` or `ja`. Each `judgment` and `explain` shape pair generally exists in both languages; `definition` and `contrast` shape pairs may exist in one or both depending on the source.

### `meta.shape`

| value | description |
|---|---|
| `judgment` | Q states a situation; A applies a named framework from the line and names a decision. Primary shape. |
| `explain` | Q asks "what is X / how does X work"; A gives a focused exposition. Used for thesis sections and structured prose. |
| `definition` | Q asks for the meaning of a term within a line; A gives the glossary-style definition. Used for glossary entries. |
| `contrast` | Q asks how two lines (or two framings within one line) differ on a situation; A cites both, names the divergence. `meta.line` is `cross-line` for these. |

### `meta.status` (optional)

The ADR's lifecycle state, extracted from its `## Status` section. One of:

| value | meaning |
|---|---|
| `accepted` | Active decision. |
| `superseded` | Replaced by a later ADR. The replacement is named in `meta.superseded_by` when extractable. |
| `withdrawn` | Cancelled without a direct successor. |
| `proposed` | Drafted but not yet adopted. |

Field is **omitted** (not `null`) when the source Status text does not match any of the above. Stage D ablation can filter on `meta.status` to compare the effect of training on accepted vs deprecated judgments.

Deprecated ADRs (`superseded` / `withdrawn`) are deliberately **included** rather than filtered out — the upstream lines treat decisions as revisable (AKC Curate / Maintain; Contemplative Agent Emptiness), so excluding the evolution would itself misrepresent the doctrine. See `docs/empirical/README.md` for the rationale.

### `meta.superseded_by` (optional)

Present only when `meta.status == "superseded"`. Stores the successor ADR identifier as a string (e.g. `"ADR-0024"`). When the Status line cites multiple successors, only the first reference encountered is recorded. The number is zero-padded to four digits regardless of how the source writes it.

## Files in `vX.Y.Z/`

- `pilot.jsonl` — hand-written precedent pairs (present in v0.1.0 only; subsequent versions absorb pilot into `train.jsonl`)
- `train.jsonl` — training split (~90% of total)
- `valid.jsonl` — validation split (~10%)
- `manifest.json` — per-line counts, total count, license, generation date, source repo commit SHAs

`train` / `valid` are produced by `scripts/build_dataset.py` from per-source intermediate JSONL files (`zenn.jsonl`, `adrs.jsonl`, `glossary.jsonl`, `thesis.jsonl`, `judgment.jsonl`). The intermediates are gitignored — they regenerate from upstream and are recorded only via `manifest.json` SHAs.

## License

CC0 1.0. See top-level `README.md` and `CITATION.cff` for full attribution.

## Loading

```python
import json

with open("corpus/v0.1.0/train.jsonl") as f:
    for line in f:
        ex = json.loads(line)
        print(ex["meta"]["line"], ex["messages"][0]["content"][:80])
```

Or via the Hugging Face mirror (recommended for training pipelines):

```python
from datasets import load_dataset

ds = load_dataset("Shimo4228/doctrine-corpus", split="train")
```

The HF mirror auto-converts the JSONL to Parquet for `pandas` / `Polars` loading as well.
