# Changelog

All notable changes to **doctrine-corpus** are recorded here. Version DOIs are assigned by Zenodo on tag push; concept DOI (line-level identifier) is recorded in this file and in `CITATION.cff` and `.zenodo.json`.

## [0.1.0] — 2026-05-22

Initial release. Concept DOI assigned by Zenodo on tag push (recorded in `CITATION.cff` and `corpus/v0.1.0/manifest.json` once available).

### Stage D — final corpus assemble + verification LoRA verdict (FAIL)

- `corpus/v0.1.0/train.jsonl` + `valid.jsonl` — 851 examples merged (pilot 5 + zenn 222 + adrs 238 + glossary 136 + thesis 24 + judgment 226) and split 766/85 with seed=42 via `scripts/build_dataset.py`
- `scripts/train.sh` — mlx-lm LoRA wrapper, ported from disposition-lora with `DATA_DIR=corpus/v0.1.0`. Pinned to `mlx-community/Qwen3-8B-4bit` for direct comparability with Phase 0 findings.md
- `eval/eval_compare.py` — base vs LoRA side-by-side generator. Reads `eval/prompt_bank.yaml` (40 prompts × 2 langs), runs base + LoRA *sequentially* (avoid 2× resident-model wedge on 16 GB Mac), and renders auto-signal Markdown report with per-line keyword hit-rate and 3-gram loop detection
- `corpus/v0.1.0/manifest.json` — stage advanced to `D`, refreshed counts (851 by line/lang/shape), new `verification_lora_verdict` field recording the FAIL
- `docs/adr/0005-stage-d-verification-lora-result.md` — early-stop verdict ADR. Auto-signals: overall keyword hit-rate **0.12** (FAIL threshold <0.30), loop-detected **67/80 = 84%** (FAIL threshold >30%). Hand-review confirms Phase 0 mannerism-wrapper pattern at stronger intensity: empty `<think></think>` (voice transferred), shimo4228-adjacent prose (domain vocabulary partially transferred), framework absent (judgment not reached), end-of-output repetition. Corpus retained as deliverable per CLAUDE.md "LoRA is verification only, not a publish target". Stage E proceeds with explicit FAIL framing in README + CITATION.cff (per ADR-0005 §Decision §2 option (a))

### Stage C — extractors + judgment Q&A synthesis

- `scripts/extract_glossary.py`, `scripts/extract_thesis.py`, `scripts/prepare_judgment_prompts.py`, `scripts/validate_judgment.py`
- `data/judgment.jsonl` — 226 judgment-shape pairs generated inside Claude Code session (no SDK call) gated by Layer 1 fire-alarm + Layer 2 rubric
- `docs/adr/0004-rubric-based-semantic-judgment-validation.md`
- `.claude/agents/judgment-pair-reviewer.md` — project-local Layer 2 rubric agent on `opus`

### Stage B — ADR / Zenn extractors for 4-line scope

- `scripts/extract_zenn.py`, `scripts/extract_adrs.py` (ported from disposition-lora and rewritten for 4-line metadata schema)
- `data/zenn.jsonl` (222), `data/adrs.jsonl` (238)

### Stage A pilot — hand-written precedent pairs

- Initial repository skeleton: README (EN + JA), CLAUDE.md, ADR index, CODEMAPS, corpus directory layout, license setup
- `corpus/v0.1.0/pilot.jsonl` — 5 hand-written Q&A pairs across AKC and Authorship Strategy lines, setting the format precedent for all subsequent extraction
- `scripts/build_dataset.py` — verbatim copy from `disposition-lora/scripts/`, ready for Stage B extension to multi-source merge
- `docs/empirical/README.md` — retrospective citing disposition-lora `findings.md`, recording why this repository pivots away from "LoRA as primary artifact"

