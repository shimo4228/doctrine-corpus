# ADRs

Design decisions for **doctrine-corpus** itself. These ADRs describe how Q&A pairs are constructed, not the doctrine being encoded — that doctrine lives in the four upstream research lines.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-corpus-as-primary-artifact.md) | Corpus as primary artifact (LoRA as derived side product) | accepted |
| [0002](0002-judgment-vs-completion-format.md) | Judgment-eliciting Q&A, not chunk-as-completion | accepted |
| [0003](0003-bilingual-pair-policy.md) | Bilingual pair policy (EN + JA as two separate pairs) | accepted |
| [0004](0004-rubric-based-semantic-judgment-validation.md) | Rubric-based semantic judgment validation (fire alarm + rubric agent) | drafted |
| [0005](0005-stage-d-verification-lora-result.md) | Stage D verification LoRA — FAIL verdict, corpus retained as standalone deliverable | accepted |

## Two layers of decisions

ADRs 0001-0003 record the project's **foundational invariants** — stances established at Stage A and made load-bearing for every later design choice. `CLAUDE.md` reproduces their key passages as a quick-reference summary; these ADR files are the canonical, fully-argued record (with Alternatives Considered and Consequences sections that `CLAUDE.md`'s summary form does not carry).

ADRs 0004 onward record **discovery-driven decisions** — non-obvious design pivots arrived at during construction. 0004 was written after Round 1 of judgment-pair generation exposed the limits of lexical-overlap validation; 0005 after the Stage D verification LoRA reproduced the Phase 0 mannerism wrapper pattern at stronger intensity.

## Format

Each ADR follows the parent-line convention: **Status / Date / Context / Decision / Alternatives Considered / Consequences** + optional Lineage section at the end pointing back to the originating session / memory.

English `NNNN-*.md` is the canonical record; Japanese `NNNN-*.ja.md` is a subordinate translation when one exists.

## When to add a new ADR

- A change in how Q&A pairs are generated (new shape, new metadata field, new source type)
- A change in license posture (corpus CC0 stays fixed; if scripts license shifts, that's an ADR)
- A change in the relationship between this repo and the parent / sibling lines (e.g., if the corpus stops being an Authorship Strategy ecosystem repo and becomes its own line — should be discussed via ADR first)
- A retrospective decision that an earlier ADR was wrong (write a superseding ADR; do not edit the original)

Routine corpus updates (new line content harvested, scripts tuned, prompt bank expanded) do not require an ADR.
