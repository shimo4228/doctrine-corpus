# doctrine-corpus

A DOI-targeted Q&A dataset that encodes the documented judgment of the shimo4228 research program (AKC / Contemplative Agent / AAP / Authorship Strategy) as training data for LLMs. The operational form of Authorship Strategy Layer 4 tactic 7 (LLM-first ingest).

Project pivot from prior `disposition-lora` Phase 0 prototype: **corpus is the primary artifact**, LoRA is a derived side product. Corpus is base-model-independent and survives base-model turnover; LoRA does not.

## Parent and sibling repositories

This repo is positioned as an **ecosystem repo of the Authorship Strategy line**, parallel in role to `contemplative-agent-data` (CA's data sibling). It is **not** a new research line, **not** a component skill — it is a derivative artifact that operationalizes one specific tactic.

- Parent line: [`authorship-strategy`](https://github.com/shimo4228/authorship-strategy) (DOI `10.5281/zenodo.20263316`)
- Source lines (corpus material harvested from):
  - [`agent-knowledge-cycle`](https://github.com/shimo4228/agent-knowledge-cycle) (DOI `10.5281/zenodo.19200726`)
  - [`contemplative-agent`](https://github.com/shimo4228/contemplative-agent) (DOI `10.5281/zenodo.19212118`, local clone: `contemplative-moltbook/`)
  - [`agent-attribution-practice`](https://github.com/shimo4228/agent-attribution-practice) (DOI `10.5281/zenodo.19652013`)
  - `authorship-strategy` itself
- Source content (non-DOI): [`zenn-content`](https://github.com/shimo4228/zenn-content)
- Phase 0 prototype: `base-model-lab/experiments/disposition-lora/` (private, not DOI'd; reference for reusable scripts)

Hub registration: appears in `shimo4228/shimo4228/graph.jsonld` as an `EcosystemRepo` node, `extends → 10.5281/zenodo.20263316`.

## Core invariant (load-bearing)

**Q&A pairs must be judgment-eliciting, not chunk-as-completion.** The Phase 0 LoRA failed because chunk-as-completion taught voice but not judgment. Every extraction script and every hand-written pair in this repository must:

1. State a situation in the Q
2. Apply the line's framework explicitly in the A (three-axis inversion, six-phase cycle, four contemplative axioms, four Business AI Quadrants, etc.)
3. Carry `meta.{line, source, lang, shape}` for downstream ablation
4. Exist in both `en` and `ja` versions wherever the source content is bilingual

Pairs that do not satisfy these are not part of the corpus. The `pilot.jsonl` written in v0.1.0 sets the precedent and the format.

## Authoring conventions

### Bilingual pair policy

Source content from the four research lines is mostly bilingual (English primary, Japanese subordinate). Each judgment example exists as two corpus entries — one EN, one JA — with the same `meta.source` and shape but different `meta.lang`. This doubles the apparent corpus size while preserving the bilingual diffusion property of Authorship Strategy.

### Shape vocabulary

| shape | Q form | A form | Used for |
|---|---|---|---|
| `judgment` | "Given situation X, how should one decide?" | Applies framework, names the decision | ADR Context → Decision mapping |
| `explain` | "What is X?" / "How does X work?" | Direct exposition | Thesis sections, structured prose |
| `definition` | "What does the term X mean in line Y?" | Glossary entry, one paragraph | Glossary terms |
| `contrast` | "How do line X and line Y differ in approach to situation Z?" | Cites both frameworks, names the divergence | Cross-line clarifications |

`judgment` is the primary shape and the highest-value content. `explain` / `definition` are reusable from the source nearly verbatim. `contrast` is the lowest-volume but most distinctive — these are the pairs that no individual line's documentation produces by itself.

### Metadata schema

Every line in `corpus/v*/*.jsonl` has shape:

```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "meta": {
    "line": "authorship-strategy",
    "source": "docs/thesis.md#three-axis-inversion",
    "lang": "en",
    "shape": "judgment"
  }
}
```

Allowed `line` values: `akc`, `contemplative-agent`, `aap`, `authorship-strategy`, `cross-line` (for `shape: contrast`), `zenn`. `lang` is `en` or `ja`. `source` is a repo-relative path or path + fragment; for `zenn` it is the article slug.

## Stage discipline

The plan ships in five stages (see `~/.claude/plans/...`). At each stage, hand-review a 20-example sample before scaling. If a stage's sample shows regression toward chunk-as-completion or voice-only transfer, stop and revisit the extractor design before generating more.

The plan's most important early-stop gate is **Stage D**: train a verification LoRA on the assembled corpus and run `eval/eval_compare.py`. If the resulting LoRA reproduces the Phase 0 "mannerism wrapper" symptom (voice transferred, content hallucinated), the corpus is still chunk-shaped and the extractors need revisiting.

## Writing conventions

- English primary, Japanese subordinate (consistent with all four parent lines)
- ADRs in `docs/adr/` follow the same Status / Date / Context / Decision / Alternatives / Consequences format as parent lines
- Empirical claims about training behaviour use "preliminary observation" tone — not "evidence of X" but "observation consistent with X"

## Out of scope (v0.1.0)

- The LoRA artifact itself (verification only, not a publish target — see `findings.md` precedent in disposition-lora)
- Attention, Not Self content (stub; v0.2.0+)
- Public benchmark evaluation (MMLU-style; v0.2.0+)
- Multilingual beyond EN/JA
- Commercial fine-tune service integration

## Hub back-propagation

On v0.1.0 release with assigned concept DOI:

- Add `EcosystemRepo` node to `shimo4228/shimo4228/graph.jsonld` extending Authorship Strategy DOI
- Add one row to hub `README.md` supporting repos table
- Add reference in `authorship-strategy/CLAUDE.md` Ecosystem repos section (not in Component skills table — this is a data sibling, not a skill)
- Update HF mirror `Shimo4228/research-program-hub` graph.jsonld + jsonl per the standard sync procedure (see `~/.claude/skills/jsonld-knowledge-graph/SKILL.md`)
