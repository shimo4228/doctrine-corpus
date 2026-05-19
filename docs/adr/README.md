# ADRs

Design decisions for **doctrine-corpus** itself. These ADRs describe how Q&A pairs are constructed, not the doctrine being encoded — that doctrine lives in the four upstream research lines.

## Index

| ADR | Title | Status |
|---|---|---|
| 0001 | Corpus as primary artifact (LoRA as derived side product) | drafted |
| 0002 | Judgment-eliciting Q&A, not chunk-as-completion | drafted |
| 0003 | Bilingual pair policy (EN + JA both as separate examples) | drafted |

## Format

Each ADR follows the parent-line convention: **Status / Date / Context / Decision / Alternatives Considered / Consequences** + optional Lineage section at the end pointing back to the originating session / memory.

English `0001-*.md` is the canonical record; Japanese `0001-*.ja.md` is a subordinate translation.

## When to add a new ADR

- A change in how Q&A pairs are generated (new shape, new metadata field, new source type)
- A change in license posture (corpus CC0 stays fixed; if scripts license shifts, that's an ADR)
- A change in the relationship between this repo and the parent / sibling lines (e.g., if the corpus stops being an Authorship Strategy ecosystem repo and becomes its own line — should be discussed via ADR first)
- A retrospective decision that an earlier ADR was wrong (write a superseding ADR; do not edit the original)

Routine corpus updates (new line content harvested, scripts tuned, prompt bank expanded) do not require an ADR.
