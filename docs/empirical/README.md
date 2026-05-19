# Empirical layer

Preliminary observations on the design of this corpus, grounded in the prior `disposition-lora` Phase 0 prototype.

Empirical claims here use **"preliminary observation"** tone, not "evidence of X" — consistent with the parent line ([`authorship-strategy/CLAUDE.md`](https://github.com/shimo4228/authorship-strategy/blob/main/CLAUDE.md) Normative vs Empirical section).

## Phase 0 retrospective (disposition-lora)

A LoRA fine-tune was attempted on Qwen3-8B-4bit using 230 chunked completion examples from Zenn articles + AKC/AAP ADRs (`/Users/shimomoto_tatsuya/MyAI_Lab/base-model-lab/experiments/disposition-lora/findings.md`, 2026-05-06). The retrospective records three primary observations:

### Observation 1: voice transfer was strong, judgment transfer was absent

The trained LoRA produced outputs that read like the author's Zenn voice — markdown structure, だ/である 発見調 tone, AKC-family vocabulary — but the **content was hallucinated**. The original retrospective phrases this as:

> The artifact behaves like a shimo4228-style mannerism wrapper more than a shimo4228 judgment oracle. It would be useful for "make this output look like a Zenn article" — useless for "what would shimo4228 think about X."

Implication for this corpus: chunk-as-completion training pairs (where the Q is the article title and the A is the chunk body) teach surface features (voice, format) but not the structured reasoning that the author actually applies. The pairs in this corpus are therefore explicitly **judgment-eliciting**: the Q states a situation and the A applies a named framework. See [`docs/adr/0002-judgment-vs-completion-format.md`](../adr/0002-judgment-vs-completion-format.md) (drafted).

### Observation 2: domain vocabulary transferred partially without semantic anchoring

The LoRA used line vocabulary (AKC, scaffold dissolution, Contemplative Agent, prohibition-strength) but the content surrounding those terms was incorrect. The model "reached for the right words but lacked enough examples to recall what they actually mean."

Implication: per-term frequency in the training set matters less than per-term **judgment context**. A glossary entry alone teaches the term; a `judgment` shape pair that uses the term inside a real situation teaches what it *does*. This corpus pairs every line's glossary terms with judgment examples that exercise them in context.

### Observation 3: dataset scale was the single largest constraint

The retrospective lists three conditions under which a Phase 1 corpus / LoRA would be worth publishing:

> - mlx-lm ships proper Qwen3.5 hybrid arch backward support → can target the user's actual stack
> - Dataset scales 10x (more articles, more ADRs, more derived examples) → judgment transfer becomes possible, not just voice
> - A specific use case emerges with a real audience (none currently identified)

Two of these are resolved at the time of this corpus:

1. **Dataset scale**: the parent ecosystem now spans four DOI-registered research lines with 193 ADRs (132 EN + 61 JA), 79 glossary terms, 2 theses, and 48 Zenn articles. The Phase 0 230-example dataset is dwarfed by even a conservative harvest.
2. **Use case + audience**: Authorship Strategy Layer 4 tactic 7 ("LLM-first ingest") names LLM-mediated channels as the primary audience and specifies the channel's structural requirements.

The unresolved condition (mlx-lm Qwen3.5 support) is sidestepped by this corpus's design: the corpus is the artifact, not the LoRA. A LoRA can be retrained against any base model when one supports the user's stack; the corpus does not depend on that.

## What this corpus does **not** claim

- That the trained model would generalize beyond shimo4228's documented judgment scope
- That voice-only LoRAs are categorically useless (Phase 0 showed they have narrow utility for stylistic mimicry; this corpus simply targets a different objective)
- That the per-line frameworks (three-axis inversion, six-phase cycle, etc.) are the only valid framings of their respective domains — they are the framings this research program records

## Verification plan (Stage D, not yet executed)

The retrospective predicts a specific failure mode: voice transferred but content hallucinated. The verification LoRA built in Stage D will be evaluated against `eval/prompt_bank.yaml` for exactly this regression. If the new corpus produces the same symptom, the extractors are still chunk-shaped and need revisiting before any release. See `scripts/train.sh` and `eval/eval_compare.py`.
