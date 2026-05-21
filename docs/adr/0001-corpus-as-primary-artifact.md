# ADR-0001: Corpus as primary artifact (LoRA as derived side product)

> **Summary.** The Phase 0 `disposition-lora` prototype published a LoRA as the deliverable and observed the "mannerism wrapper" failure mode: voice transferred, judgment did not. This project inverts the relationship — the **corpus** is the primary, durable, base-model-independent artifact; LoRA training, if it happens, is verification only and never the deposit target. The pivot is load-bearing for every other design decision in this repository.

## Status
accepted

## Date
2026-05-20

## Context

The Phase 0 prototype `base-model-lab/experiments/disposition-lora/` (run date 2026-05-06, retrospective in `findings.md`) treated the LoRA adapter as the publishable artifact. ~230 chunked completion examples from Zenn articles + AKC / AAP ADRs were used to fine-tune Qwen3-8B-4bit. The retrospective records the outcome verbatim:

> The artifact behaves like a shimo4228-style mannerism wrapper more than a shimo4228 judgment oracle. It would be useful for "make this output look like a Zenn article" — useless for "what would shimo4228 think about X."

Three structural problems made the LoRA-as-deliverable path costly:

1. **Base-model coupling.** The LoRA targets Qwen3-8B-4bit. Qwen3.5-9B (the user's actual Ollama stack) cannot consume the same adapter because mlx-lm 0.31.3 does not support the Qwen3.5 hybrid architecture's backward pass. The adapter is therefore for *someone else's stack*, and even that audience evaporates the moment a new base model supersedes Qwen3-8B.

2. **Maintenance asymmetry.** A LoRA artifact needs a model card, an inference recipe, a licensing decision per base model, and a per-version DOI on Zenodo if anyone is to find it later. The cost scales with the number of supported base models. A corpus has one license, one DOI, one README.

3. **Verification ambiguity.** When a LoRA is the deliverable, "does the corpus encode the right judgment?" and "does this specific (base, iter, lr, batch) configuration absorb it?" collapse into a single pass/fail. The interesting question — *is the corpus structurally sound?* — becomes inseparable from the training engineering. Phase 0's FAIL could not distinguish between "the data is chunk-shaped" and "8B-4bit is too small to recover what's there."

These problems all point to the same axis: a fine-tuned model is a *snapshot of a training process at a moment in time against a specific base*, while a corpus is a *standalone semantic artifact that survives base-model turnover*. The Authorship Strategy line's preference hierarchy (`creative reuse > training > investigation`) names this directly — `training` is a derived consumption mode of `creative reuse`-shaped material, not the other way around.

## Decision

`doctrine-corpus` makes the corpus the **primary artifact**. Specifically:

1. **`corpus/v0.1.0/{train,valid,pilot}.jsonl` is the deposit target.** Zenodo deposits version this directory; the concept DOI points at the corpus as a `Dataset` (schema.org `CreativeWork` subclass `Dataset`), not at a derived adapter.

2. **LoRA training is verification only.** `scripts/train.sh` + `eval/eval_compare.py` exist to run an *early-stop gate* that detects the Phase 0 mannerism wrapper before deposit. Their outputs (`outputs/adapters/`, `outputs/eval/`, `outputs/logs/`) are gitignored. No LoRA artifact is uploaded to HuggingFace, no `MODEL_CARD.md` is written, no derivative DOI is requested.

3. **The corpus is base-model-independent by construction.** Pair format is the OpenAI-style `messages` array, which is the de facto interchange format across mlx-lm, transformers, vLLM, and the major closed APIs. Metadata (`meta.{line, source, lang, shape}`) is auxiliary information that survives format translation. Nothing in the corpus references a specific tokenizer, chat template, or weight checkpoint.

4. **Reuse hierarchy is documented.** Downstream consumers may use the corpus for any of: in-context augmentation (RAG), training-data ingestion (their own fine-tunes against their own base models), retrieval-augmented evaluation suites, or simple human reading. The license (CC0-1.0) and the absence of any base-model lock-in are deliberate consequences of this ordering.

## Alternatives considered

**LoRA as primary (Phase 0 approach).** Rejected. The Phase 0 retrospective explicitly recommended against promoting that artifact to a published Phase 1 release: "do **not** promote this Phase 0 artifact to a published Phase 1 release." The base-model-coupling and maintenance-asymmetry problems above are why.

**Joint deposit of corpus + LoRA.** Considered and rejected. The joint deposit invites readers of the hub `EcosystemRepo` row to evaluate the corpus *through* the LoRA's success — the same trap Phase 0 fell into. Coupling the two artifacts under one DOI re-creates the verification-ambiguity problem we are trying to escape.

**No LoRA at all (corpus-only with no verification probe).** Considered and rejected, but only weakly — corpus-only is a defensible posture if one is willing to trust that the judgment-eliciting structure (ADR-0002) is sufficient without empirical verification. We chose to retain the LoRA *purely as a probe* because Phase 0's mannerism wrapper finding is the one signal we cannot derive from inspecting the corpus statically. The probe is cheap (~3 hours local), and its FAIL verdict (recorded in ADR-0005) is itself useful — it tells us where the (data scale × shape distribution × base model) interaction sits relative to the judgment-transfer regime.

## Consequences

### Immediate (structural)

- `CLAUDE.md` opens with the pivot in its very first paragraph, before the parent-line and ADR-format conventions. It is the load-bearing project statement.
- `corpus/v0.1.0/manifest.json` describes the *corpus* as the artifact; the `verification_lora_verdict` field is subordinate metadata, not a gate on the corpus's validity.
- All extractor scripts target `corpus/v0.1.0/*.jsonl`; the LoRA `outputs/` directory is downstream and gitignored.
- ADR-0005 (Stage D verdict) records a FAIL on the LoRA probe without invalidating the corpus, which is only possible under this pivot. Under the Phase 0 framing, a FAIL would have invalidated the deliverable.

### Downstream

- The corpus can be re-tested against future base models (Qwen3.5-9B once mlx-lm supports it, or any newer model) without re-deriving the dataset. New verification LoRAs can be trained against the same `corpus/v0.1.0/train.jsonl` indefinitely.
- The corpus is suitable for the `creative reuse > training > investigation` preference hierarchy of the parent Authorship Strategy line — readers can absorb it directly (RAG, in-context, plain reading) without ever running the LoRA path.

### Open

- Whether the corpus, on its own, achieves the "LLM-mediated diffusion" Authorship Strategy intends is an empirical question this corpus cannot answer about itself; it depends on downstream consumption that lives outside this repo's boundaries (citation counts on the eventual Zenodo deposit, RAG-system inclusion, training-set inclusion in derived models).

## Lineage

- Phase 0 retrospective: `base-model-lab/experiments/disposition-lora/findings.md` (2026-05-06)
- Empirical layer record: `docs/empirical/README.md` Phase 0 retrospective section
- Companion invariants: ADR-0002 (Q&A shape), ADR-0003 (bilingual pair policy)
- Companion verification: ADR-0005 (Stage D verdict)
