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

The plan's most important early-stop gate is **Stage D**: train a verification LoRA on the assembled corpus and run `eval/eval_compare.py`. If the resulting LoRA reproduces the Phase 0 "mannerism wrapper" symptom (voice transferred, content hallucinated), the corpus is still chunk-shaped and the extractors need revisiting. The LoRA itself is **verification only, not a publish target** — the corpus is the deliverable; the LoRA is used as a disposable test runner against `eval/prompt_bank.yaml`.

## Judgment generation protocol (Stage C session-mediated synthesis)

`data/judgment.jsonl` is generated **inside a Claude Code session**. No Anthropic / OpenAI SDK call. Rationale: the author runs on Claude Max (flat subscription); SDK calls would add metered cost and an unnecessary API key management surface. This is also the recursive application of Authorship Strategy Layer 4 tactic 7 (LLM-first ingest) — the corpus that operationalizes the tactic is itself produced in an LLM-first workflow.

### Why this file exists at all

The Stage B `data/adrs.jsonl` carries one judgment pair per ADR per language, with Q = `{framework prefix}\n\n{ADR Context verbatim}` and A = `{Decision}`. That gives only **one situation entry per Decision** — and the Q is the original Context near-verbatim. Training on that alone risks the Phase 0 failure mode: the model learns the surface mapping from Context phrasing to Decision phrasing, not the judgment itself.

`judgment.jsonl` adds **K=2 alternative situations per ADR** that reach the same Decision through different entry points. With the original ADR pair plus K=2 alternatives, every Decision has three (or more) situation entries, all decoupled from the original Context surface form. This is what shifts the corpus from chunk-as-completion shape to judgment-eliciting shape.

### Pipeline

1. `python scripts/prepare_judgment_prompts.py` — emits `data/judgment_prompts.jsonl` (113 entry × K=2). LLM call: zero.
2. **Round 1 gate**: in-session generation of the first 10 entries × K=2 = 20 pairs into `data/judgment.jsonl`. Hand-review mandatory.
3. `python scripts/validate_judgment.py data/judgment.jsonl --top-fail 5` — **Layer 1 fire alarm** (schema + Q novelty + Q anti-chunk).
4. Invoke the `judgment-pair-reviewer` Claude Code agent — **Layer 2 rubric** (8-criterion semantic verdict).
5. User spot-checks the rubric's WEAK/FAIL findings.
6. Round 2–7: ~40 entries × K=2 = ~80 pairs per round, with `--tail 80` Layer 1 + Layer 2 review after each round.

### Validation layers

Validation is split into two layers (see [ADR-0004](docs/adr/0004-rubric-based-semantic-judgment-validation.md)):

- **Layer 1 — fire alarm** (`scripts/validate_judgment.py`): schema, q_novelty (verbatim 200-char detection in Q), q_anti_chunk (regex). Catches structural and obvious surface regressions only. Cannot measure judgment quality.
- **Layer 2 — rubric** (`doctrine-corpus/.claude/agents/judgment-pair-reviewer.md`): 8-criterion PASS/WEAK/FAIL judgment over Decision Equivalence, Framework Application, Situation Novelty, K=2 Facet Diversity, Style-without-Substance Guard, Bilingual Pair Equivalence, and delegated metadata / anti-chunk confirmations. Project-local agent on `opus`.

Run Layer 1 first; if it passes, invoke Layer 2 via the agent. User spot-check of Layer 2's WEAK/FAIL findings is mandatory before the next round.

### Round 1 early-stop conditions

Stop and re-design the prompt on any of:

**Fire-alarm signals (`scripts/validate_judgment.py`):**
- `q_novelty:verbatim_200` in 1+ pairs
- `q_anti_chunk:*` matches in 3+ pairs
- `schema:*` failures in any pair

**Rubric signals (`judgment-pair-reviewer` agent):**
- FAIL rate > 15% on Criterion 1 (Decision Equivalence), 2 (Framework Application), or 5 (Style-without-Substance Guard) — load-bearing axes
- WEAK rate > 30% on Criterion 4 (K=2 Facet Diversity) — facet axes too narrow

User spot-check of WEAK/FAIL flagged pairs is mandatory before Round 2.

### Per-pair invariants (every generated pair must hold)

- `meta.line` and `meta.lang` match the source ADR
- `meta.source` is the source ADR path with `#decision` fragment (same as `data/adrs.jsonl` for that ADR)
- `meta.shape == "judgment"`
- Q presents a **new** situation, not the original Context
- A names at least one term from the line's `judgment_synthesis_framework_keywords` (see `scripts/line_templates.yaml`)
- A reaches a Decision **logically equivalent** to the source ADR's Decision — paraphrasing OK, semantic change is not

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
