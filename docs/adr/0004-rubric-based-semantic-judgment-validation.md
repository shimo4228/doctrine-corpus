# ADR-0004: Rubric-based semantic judgment validation

> **Summary.** Judgment-pair validation is split into two layers. Layer 1 (fire alarm, `scripts/validate_judgment.py`) catches structural and obvious surface regressions via schema, q_novelty, and q_anti_chunk checks only. Layer 2 (rubric, `doctrine-corpus/.claude/agents/judgment-pair-reviewer.md`, a project-local Claude Code agent on `opus`) applies an 8-criterion PASS/WEAK/FAIL rubric over Decision Equivalence, Framework Application, Situation Novelty, K=2 Facet Diversity, Style-without-Substance, and Bilingual Pair Equivalence. The vocabulary-frequency overlap and keyword-presence checks that previously sat in the script are removed because they cannot measure judgment quality and gave false-PASS on the exact failure mode the corpus exists to avoid.

## Status
drafted

## Date
2026-05-20

## Context

`doctrine-corpus` v0.1.0 Stage C uses `scripts/validate_judgment.py` as the round-by-round gate during session-mediated judgment generation. The script runs five checks per pair:

1. `schema` — meta keys present, `shape == "judgment"`
2. `decision_drift_score` — top-10 most-frequent content tokens from the source ADR's Decision must appear in the generated A with ≥50% coverage
3. `has_framework_keyword` — at least one term from the line's `judgment_synthesis_framework_keywords` must appear in the generated A
4. `q_novelty_violation` — the generated Q must not contain the source ADR's Context first 200 characters verbatim
5. `q_anti_chunk_violation` — the generated Q must not match chunk-as-completion regex patterns (`write a Zenn article`, `explain ADR-N`, etc.)

Round 1 (10 entries × K=2 = 20 pairs, written 2026-05-20) exposed three problems with this design.

**Problem 1: vocabulary overlap cannot measure judgment equivalence.** A generated A can echo the source Decision's most-frequent tokens and still reach a *different* decision, or reach the *same* decision but through hallucinated reasoning. This is the Phase 0 failure mode `disposition-lora` documented in `docs/empirical/README.md`: "voice transferred, content hallucinated — the artifact behaves like a shimo4228-style mannerism wrapper more than a shimo4228 judgment oracle." Vocabulary-frequency overlap is, by construction, sensitive to mannerism and insensitive to judgment. The Phase 0 retrospective is exactly the regression the corpus exists to avoid; the script's primary semantic check is biased toward false-PASS on it.

**Problem 2: keyword presence is decoration, not application.** `has_framework_keyword` passes as long as one framework term appears anywhere in the generated A. A pair where the framework term is name-dropped but the decision is reached *without using it* — the LLM equivalent of citing without reading — scores PASS. The Core invariant in CLAUDE.md requires the framework to be applied "explicitly"; the check requires only that it appears.

**Problem 3: K=2 facet diversity has no check at all.** CLAUDE.md "Judgment generation protocol" specifies that K=2 alternative pairs per ADR must "reach the same Decision through *different* entry points." Round 1 produced two ADR-0009 alternatives both anchored on the same facet (cycle vs harness), and the script returned PASS on both. The whole purpose of K=2 — broadening the surface of situations from which the same Decision is recovered — is defeated when both alternatives rehash the same facet, and there is currently no mechanism to detect that.

These three problems are not implementation bugs in the script — they are properties of the chosen validation approach (lexical surface signal on individual pairs). Lexical overlap and keyword search are tools for *catching obvious regression*; they are not tools for *measuring judgment quality*. The literature on training-data evaluation (G-Eval EMNLP 2023, Prometheus 2 EMNLP 2024, FLASK ICLR 2024, MT-Bench NeurIPS 2023, JudgeBench ICLR 2025, Anthropic eval docs) is consistent: semantic judgment requires LLM-as-judge with an explicit rubric, chain-of-thought before verdict, per-criterion isolation, and human spot-check calibration. Vocabulary overlap correlates with human judgment at Spearman ~0.2 (BLEU/ROUGE); rubric-based LLM-judge reaches Spearman ~0.5 on the same task (G-Eval).

A second pressure is structural. The script and the agent are two different *kinds* of validator — one runs deterministically per pair and catches structural / regex / schema problems; the other runs probabilistically per group and catches semantic / facet / equivalence problems. Bundling both inside the script forces the script to do work it cannot do well, and forces the corpus to wait for Stage D's LoRA `eval_compare.py` to detect what should be caught at generation time.

## Decision

Validation is split into two layers.

### Layer 1 — fire alarm (`scripts/validate_judgment.py`)

Retains exactly three categories of check:

- `schema` — required meta keys, `shape == "judgment"`, non-empty messages
- `q_novelty` — verbatim 200-character Context-prefix detection in Q
- `q_anti_chunk` — chunk-as-completion regex pattern detection in Q (EN + JA pattern tables)

Removed: `decision_drift_score`, `has_framework_keyword`, and the `extract_content_tokens` / `extract_decision` helpers that supported them. The script's `Aggregate metrics` block loses `Avg Decision-token coverage` and `Framework keyword inclusion`; `Q novelty rate` is retained.

Role statement: the script is a **structural and regex-pattern gate**. It does not measure judgment quality. It is run first, before the agent, and a Layer 1 failure stops the round before semantic validation is attempted.

### Layer 2 — rubric (`doctrine-corpus/.claude/agents/judgment-pair-reviewer.md`)

A new project-local Claude Code agent. Eight criteria, each scored PASS / WEAK / FAIL (matching the user's harness convention — no numeric 1–10 scoring):

1. **Decision Equivalence** (load-bearing) — generated A reaches a decision logically equivalent to the source ADR's Decision; load-bearing qualifications preserved
2. **Framework Application** (load-bearing) — line's framework term is the *reasoning lever* that produces the decision, not decoration
3. **Situation Novelty** — Q presents a situation distinct from the source ADR Context in setting, actor, or trigger
4. **K=2 Facet Diversity** (set-level, load-bearing) — the K=2 alternatives pull from different facets (actor / domain / trigger / horizon / scope) of the same Decision
5. **Style-without-Substance Guard** (load-bearing) — direct check against the Phase 0 mannerism-wrapper failure mode
6. **Bilingual Pair Equivalence** — when EN+JA siblings exist, both reach the same Decision through translation-natural differences
7. **Metadata Integrity** — confirms the script's schema verdict (delegation, not re-implementation)
8. **Q-Anti-Chunk** — confirms the script's regex verdict (delegation, not re-implementation)

Aggregation rule:
- Any FAIL on C1, C2, C3, C4, C5, C7, C8 → pair FAIL
- FAIL on C6 (when applicable) → pair FAIL
- No FAIL, any WEAK on C1, C2, C4, C5 → pair WEAK
- No FAIL, WEAK only on C3, C6 → pair WEAK
- Otherwise → pair PASS

Bias mitigations built into the rubric: position-bias mitigation for C4 (judge evaluates both K=2 orderings), verbosity-bias mitigation (judge counts load-bearing claims, not sentence count), self-enhancement-bias mitigation (source-span citation required for every verdict), chain-of-thought before verdict, per-criterion isolation.

### Agent placement

The agent lives at `doctrine-corpus/.claude/agents/judgment-pair-reviewer.md` — **project-local**, not global. Its rubric refers to corpus-specific entities (`data/adrs.jsonl`, `scripts/line_templates.yaml`, the four lines `akc / contemplative-agent / aap / authorship-strategy`) and its facet axes are corpus-specific. A global agent would carry the wrong assumptions to unrelated repositories. This is the first project-local agent in any shimo4228 research repo and establishes `<project>/.claude/agents/` as a valid namespace for corpus-specific reviewers.

Judge model: `opus`. This matches the precedent set by `~/.claude/agents/source-fidelity-checker.md` — judgment-correctness work uses opus, throughput work uses sonnet. Cost is irrelevant under the user's Claude Max flat-rate subscription.

### Round-by-round workflow

```
Round N generation (in-session)
  ↓
[1] validate_judgment.py --tail N    ← fire alarm (Layer 1)
  ↓ fire-alarm signals → STOP, fix prompt
[2] judgment-pair-reviewer agent     ← rubric (Layer 2)
  ↓ rubric signals → STOP or SPOT-CHECK
[3] User spot-check of WEAK/FAIL findings
  ↓
[4] Round N+1 go signal
```

`CLAUDE.md` "Round 1 early-stop conditions" is rewritten to enumerate fire-alarm signals (script) and rubric signals (agent) separately. Per-pair invariants (Q presents new situation, A names framework term, etc.) are unchanged — they are the spec the rubric enforces.

## Alternatives Considered

### Embedding-based drift detection (BERTScore / SBERT cosine)

Replace `decision_drift_score`'s lexical overlap with semantic embedding cosine similarity. **Rejected.** Embedding cosine is still a surface signal — it measures whether the two strings *talk about the same things*, not whether they *reach the same conclusion*. It is more expensive than token overlap, produces a number that is hard to threshold across diverse ADR lengths, and most importantly still cannot detect the Phase 0 failure mode (mannerism with correct topic).

### External LLM-judge via Anthropic SDK (Prometheus 2, G-Eval verbatim)

Run a separate Anthropic API call per pair using the Prometheus 2 protocol or the G-Eval prompt template. **Rejected** for two reasons. First, it breaks the in-session zero-SDK constraint that operationalizes Authorship Strategy Layer 4 tactic 7 ("LLM-first ingest") — the corpus that operationalizes the tactic should itself be produced and validated inside the LLM-first workflow, not through metered API calls. Second, the Claude Max subscription already provides opus subagents inside the harness; using subagents is the no-cost equivalent and avoids API key management.

### Defer all semantic checking to Stage D `eval/eval_compare.py`

Skip the rubric layer at generation time; let the verification LoRA's behavior on the prompt bank catch semantic problems. **Rejected.** By Stage D the corpus is already assembled and the LoRA is the unit of analysis — finding that the corpus is chunk-shaped at that point means re-running every round's generation. The round-by-round gate is the leverage point; deferring loses it. The Stage D LoRA eval remains the *final* corpus-level check; the rubric is the *per-round* check.

### Global agent in `~/.claude/agents/judgment-pair-reviewer.md`

Place the new agent alongside `source-fidelity-checker`, `essay-reviewer`, etc. **Rejected.** The rubric depends on `data/adrs.jsonl`, `scripts/line_templates.yaml`, and the specific four-line vocabulary of this corpus. Other repositories do not have these inputs; a global agent would either misfire or carry hard-coded paths that pollute the global namespace.

### Keep the current validator and add the rubric agent on top

Leave `decision_drift_score` and `has_framework_keyword` in place; have the agent run additionally. **Rejected.** The two broken checks are not just unhelpful — they actively bias evaluation toward false-PASS on the Phase 0 failure mode and would create conflicting verdicts (script PASS but agent FAIL). Cleaner to remove them and let the rubric be the sole semantic gate.

## Consequences

**Validator size shrinks.** `scripts/validate_judgment.py` drops from ~361 LOC to ~150 LOC. The removed code (`extract_content_tokens`, `decision_drift_score`, `has_framework_keyword`, `extract_decision`) is gone, not commented out — vocabulary overlap is rejected as a methodology, not as an implementation.

**CLAUDE.md "Round 1 early-stop conditions" rewritten.** The previous conditions cited validator metrics that no longer exist (`drift > 30%`, `framework < 60%`). The new conditions split into fire-alarm signals (any verbatim-200 violation, 3+ anti-chunk matches, any schema failure) and rubric signals (FAIL > 15% on load-bearing criteria C1/C2/C5, WEAK > 30% on C4).

**New namespace precedent.** `<project>/.claude/agents/` becomes a valid namespace in shimo4228 research repos. Future corpus-specific reviewers (e.g., a hypothetical `glossary-pair-reviewer` for the glossary extraction) can use the same pattern. Global reviewer agents remain the default for domain-portable work; project-local agents are reserved for cases where the rubric or canonical sources are corpus-specific.

**User spot-check workload becomes structured.** Previously the workflow assumed the user would hand-review every Round 1 pair. The new workflow expects the user to read only the rubric's WEAK/FAIL flagged pairs plus N=5 random PASS pairs per round for calibration. Workload scales with rubric strictness, not with corpus size.

**Calibration risk.** The rubric is itself a Claude Code agent on `opus`; its verdicts are not ground truth. JudgeBench (ICLR 2025) shows the strongest LLM judges still cap at ~64% accuracy on reasoning correctness. The agent must be calibrated against the author's judgment on the first few rounds — if the agent's WEAK/FAIL flags disagree with the author's read of the same pairs, the rubric prompt needs adjustment, not the corpus. This is the Anthropic-eval-docs-recommended calibration step and is explicit in the workflow.

**Round 1 is not re-generated by this ADR.** The 20 pairs in `data/judgment.jsonl` from Round 1 (2026-05-20) are retained. They are re-evaluated under the new rubric as the first calibration data point. If the rubric flags the ADR-0009 Alt 2 facet-diversity issue identified during the previous gate review, that confirms the rubric is operating as designed.

**Stage D `eval_compare.py` is unchanged.** The LoRA-driven behavioral eval at corpus assembly time remains the final check. The rubric is upstream of it, not a replacement.

## Lineage

- Originating session: 2026-05-20, doctrine-corpus Round 1 hand-review (`.scratch/round1_gen.py` artifacts, retained for reproducibility)
- Triggered by: user observation that script-based vocabulary check cannot measure semantic implementation
- External research distilled into rubric design: G-Eval ([arXiv:2303.16634](https://arxiv.org/abs/2303.16634)), Prometheus 2 ([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.248.pdf)), FLASK ([arXiv:2307.10928](https://arxiv.org/pdf/2307.10928)), MT-Bench / LLM-as-Judge ([arXiv:2306.05685](https://arxiv.org/abs/2306.05685)), JudgeBench ([arXiv:2410.12784](https://arxiv.org/abs/2410.12784)), Reference-Guided Verdict ([arXiv:2408.09235](https://arxiv.org/pdf/2408.09235)), LIMA ([arXiv:2305.11206](https://arxiv.org/pdf/2305.11206)), Anthropic eval docs ([docs.anthropic.com/en/docs/test-and-evaluate/develop-tests](https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests))
- Implementation plan: `~/.claude/plans/radiant-brewing-rabbit.md`
