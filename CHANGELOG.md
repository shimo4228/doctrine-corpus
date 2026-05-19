# Changelog

All notable changes to **doctrine-corpus** are recorded here. Version DOIs are assigned by Zenodo on tag push; concept DOI (line-level identifier) is recorded in this file and in `CITATION.cff` and `.zenodo.json`.

## [Unreleased]

### Stage A pilot — hand-written precedent pairs

- Initial repository skeleton: README (EN + JA), CLAUDE.md, ADR index, CODEMAPS, corpus directory layout, license setup
- `corpus/v0.1.0/pilot.jsonl` — 5 hand-written Q&A pairs across AKC and Authorship Strategy lines, setting the format precedent for all subsequent extraction
- `scripts/build_dataset.py` — verbatim copy from `disposition-lora/scripts/`, ready for Stage B extension to multi-source merge
- `docs/empirical/README.md` — retrospective citing disposition-lora `findings.md`, recording why this repository pivots away from "LoRA as primary artifact"

### Not yet present

- Stage B: ported `extract_zenn.py` and rewritten `extract_adrs.py` for the 4-line scope
- Stage C: new `extract_judgment_qa.py` (LLM-mediated), `extract_glossary.py`, `extract_thesis.py`
- Stage D: built `corpus/v0.1.0/train.jsonl` + `valid.jsonl`, verification LoRA outputs
- Stage E: `.zenodo.json`, `llms.txt`, `llms-full.txt`, `graph.jsonld`, HF mirror upload, hub back-propagation

## [0.1.0] — TBD (Zenodo deposit pending)

Initial release. Concept DOI: TBD.
