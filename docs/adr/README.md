# ADRs

Design decisions for **doctrine-corpus** itself. These ADRs describe how Q&A pairs are constructed, not the doctrine being encoded — that doctrine lives in the four upstream research lines.

## Index

| ADR | Title | Status |
|---|---|---|
| [0004](0004-rubric-based-semantic-judgment-validation.md) | Rubric-based semantic judgment validation (fire alarm + rubric agent) | drafted |
| [0005](0005-stage-d-verification-lora-result.md) | Stage D verification LoRA — FAIL verdict, corpus retained as standalone deliverable | accepted |

## Numbering

ADRs in this repository start at **0004**, not 0001. The first three numeric slots are reserved for the project's foundational invariants — *corpus as primary artifact (LoRA as derived side product)*, *judgment-eliciting Q&A (not chunk-as-completion)*, and *bilingual pair policy* — but those invariants live as load-bearing sections in [`CLAUDE.md`](../../CLAUDE.md), not as standalone ADR files. They are foundational stance, not discovered-during-build decisions, and `CLAUDE.md` is the canonical record for them.

ADRs 0004 onward record **discovery-driven decisions** — non-obvious design pivots arrived at during construction (e.g., 0004 after Round 1 judgment-pair validation exposed the limits of lexical overlap; 0005 after the Stage D verification LoRA reproduced the Phase 0 mannerism wrapper pattern). Reserve 0001-0003 if those invariants ever need to be lifted into standalone records (e.g., for renegotiation against a new parent-line decision); until then they stay in `CLAUDE.md`.

## Format

Each ADR follows the parent-line convention: **Status / Date / Context / Decision / Alternatives Considered / Consequences** + optional Lineage section at the end pointing back to the originating session / memory.

English `NNNN-*.md` is the canonical record; Japanese `NNNN-*.ja.md` is a subordinate translation when one exists.

## When to add a new ADR

- A change in how Q&A pairs are generated (new shape, new metadata field, new source type)
- A change in license posture (corpus CC0 stays fixed; if scripts license shifts, that's an ADR)
- A change in the relationship between this repo and the parent / sibling lines (e.g., if the corpus stops being an Authorship Strategy ecosystem repo and becomes its own line — should be discussed via ADR first)
- A retrospective decision that an earlier ADR was wrong (write a superseding ADR; do not edit the original)

Routine corpus updates (new line content harvested, scripts tuned, prompt bank expanded) do not require an ADR.
