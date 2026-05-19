# Architecture

File-level guide to **doctrine-corpus**. For the concept-level relationship map see `graph.jsonld` (added in Stage E).

## Layout

```
doctrine-corpus/
├── README.md / README.ja.md   # entry points (EN primary, JA subordinate)
├── CLAUDE.md                  # agent-facing context: invariants, conventions, hub back-prop
├── CHANGELOG.md               # version log with stage markers
├── CITATION.cff               # canonical citation, links to sibling DOIs
├── .zenodo.json               # (Stage E) Zenodo deposit metadata + sibling identifiers
├── pyproject.toml             # dependencies grouped: core / extract / train
├── llms.txt + llms-full.txt   # (Stage E) AI-facing navigators
├── graph.jsonld               # (Stage E) concept-level JSON-LD
│
├── docs/
│   ├── CODEMAPS/
│   │   └── architecture.md    # this file
│   ├── adr/
│   │   ├── README.md          # ADR index
│   │   ├── 0001-corpus-as-primary-artifact.md       # (drafted in Stage A)
│   │   ├── 0002-judgment-vs-completion-format.md
│   │   └── 0003-bilingual-pair-policy.md
│   ├── thesis.md              # (Stage C) corpus design thesis
│   ├── glossary.md            # (Stage C) terms used by this corpus
│   └── empirical/
│       └── README.md          # disposition-lora retrospective
│
├── corpus/
│   ├── README.md              # schema spec for the JSONL examples
│   └── v0.1.0/
│       ├── pilot.jsonl        # (Stage A) hand-written precedent pairs
│       ├── train.jsonl        # (Stage D) merged + 90/10 split
│       ├── valid.jsonl        # (Stage D)
│       └── manifest.json      # per-line counts, license, generation date
│
├── scripts/
│   ├── build_dataset.py       # (Stage A) verbatim copy from disposition-lora
│   ├── extract_zenn.py        # (Stage B) ported from disposition-lora
│   ├── extract_adrs.py        # (Stage B) rewritten for 4-line scope
│   ├── extract_glossary.py    # (Stage C) new
│   ├── extract_thesis.py      # (Stage C) new
│   ├── extract_judgment_qa.py # (Stage C) new, LLM-mediated, core script
│   └── train.sh               # (Stage D) ported from disposition-lora
│
└── eval/
    ├── README.md
    ├── prompt_bank.yaml       # (Stage C) 40 prompts = 10 per line × 4 lines
    └── eval_compare.py        # (Stage D) base vs adapted side-by-side
```

## Role boundary: this repo vs upstream lines

This repository **does not author new ideas**. Every Q&A pair traces back to source content in the four upstream research lines (AKC / Contemplative Agent / AAP / Authorship Strategy) or in `zenn-content`. The reformulation work — converting ADRs and theses into Q&A — is the only original output.

This means:

- **Upstream content updates → re-run extractors** (Stage B/C scripts) to regenerate Q&A. Do not edit `corpus/v*/*.jsonl` by hand to track upstream changes; the source attribution would drift.
- **Corpus design ADRs** (`docs/adr/0001`, `0002`, `0003`) describe the reformulation logic and the bilingual / metadata invariants. They do not duplicate doctrine from upstream lines.

## Versioning

Each `corpus/vX.Y.Z/` directory is an immutable snapshot. A new corpus version requires a new directory plus a new Zenodo version DOI. The concept DOI is stable across versions and indexes all of them.

`pilot.jsonl` lives only in the v0.1.0 release directory and exists to record the hand-written precedent. From v0.2.0+ the corpus consists of `train.jsonl` + `valid.jsonl` only; pilot pairs migrate into `train.jsonl` (per `meta.shape` filtering, they remain identifiable).

## graph.jsonld vs CODEMAPS (consistent with parent line)

`graph.jsonld` (added Stage E) and this `CODEMAPS/architecture.md` cover the same project at different abstraction layers:

- **CODEMAPS = file-level**: "where does X live in this repo" in prose
- **graph.jsonld = concept-level**: "what is X and how does it relate to Y" in schema.org JSON-LD triples

The two are complementary, not duplicative. New ADRs / concepts must update both.
