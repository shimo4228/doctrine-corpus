# ADR-0005: Stage D verification LoRA — FAIL verdict, corpus retained as standalone deliverable

> **Summary.** The Stage D verification LoRA reproduces the Phase 0 "mannerism wrapper" failure mode at a stronger intensity: 84% of LoRA outputs trigger the 3-gram loop detector and the overall framework-keyword hit-rate is 12% (early-stop FAIL thresholds: >30% and <30% respectively). Voice and structure transfer cleanly across all four lines, but the LoRA does not reach the expected `Decision` on the rubric prompts — it hallucinates plausible-looking, line-adjacent content while bypassing the framework. The corpus deliverable (`corpus/v0.1.0/`) is retained — the LoRA was designed as a disposable probe, not as a deposit target — and Stage E (publish / hub back-propagation) does not proceed under this verdict. v0.2.0 work should target the data-scale and shape-distribution hypotheses described under Consequences.

## Status
accepted

## Date
2026-05-21

## Context

The Stage D plan in `~/.claude/plans/stagec-stage-d-loop-magical-kazoo.md` defines the verification LoRA as a "disposable test runner" against `eval/prompt_bank.yaml`, with a single early-stop gate: **if the LoRA reproduces the Phase 0 `mannerism wrapper` symptom (voice transferred, content hallucinated), the corpus is still chunk-shaped and the extractors need revisiting**. The gate has two auto-signal axes (loop-detection rate, framework-keyword hit-rate) and a hand-review axis (does the LoRA reach `expected_decision_pattern` on 12 spot-check prompts).

This ADR records the result of running that gate against the assembled `corpus/v0.1.0/` (851 examples = pilot 5 + zenn 222 + adrs 238 + glossary 136 + thesis 24 + judgment 226) on a `mlx-community/Qwen3-8B-4bit` LoRA trained inside this repo's M2 16 GB Mac.

### Run conditions

- Base model: `mlx-community/Qwen3-8B-4bit` (Phase 0 used the same; Qwen3.5 hybrid arch OOMs under mlx-lm 0.31.3 backward — see disposition-lora `findings.md`)
- LoRA adapter: 9.699 M trainable params (0.118% of 8.19 B), num-layers 16, batch 1, lr 1e-5, grad-checkpoint on
- Iterations: **300 actual** (planned 400; full run stalled at iter 380 in macOS `UN` uninterruptible-sleep state under memory pressure, peak free pages ~144 MB. SIGCONT did not unwedge. iter 300 checkpoint matches the live `adapters.safetensors` by MD5 and is used as the final probe weight. 300 iter × 851 examples ≈ 1.13× the total token-touches Phase 0 had at iter 400 × 230 examples, so the under-iteration is not the load-bearing factor.)
- Eval: `eval/eval_compare.py` over `eval/prompt_bank.yaml` (40 prompts × 2 langs = 80 entries), base + LoRA sequentially loaded to avoid the 2× resident-model wedge that took down the train run

Train loss trajectory at iter 50 / 100 / 200 / 300 (val-noise smoothed): 2.430 / Saved / 2.415 / Saved — Phase 0 reached 1.577 at iter 400 on a 4× smaller corpus, so the per-example loss floor for this corpus on this base is reached more slowly per the broader gradient. Loss never went to NaN; the failure mode is not optimization, it is what the optimization minimized toward.

### Auto signals from `outputs/eval/compare.md`

| line | prompts | mean keyword hit-rate | loop-detected count |
|---|---:|---:|---:|
| aap | 20 | 0.15 | 17 |
| akc | 20 | 0.11 | 17 |
| authorship-strategy | 20 | 0.10 | 16 |
| contemplative-agent | 20 | 0.12 | 17 |
| **overall** | **80** | **0.12** | **67** |

- **Loop-detected**: 67/80 = **84%** vs FAIL threshold > 30%
- **Keyword hit-rate overall**: **12%** vs FAIL threshold < 30%
- Both Stage D early-stop axes failed. Per the plan: `FAIL → ADR-0005 に "extractor revisit 必要" と記録、Stage D 内で停止`

### Hand-review of spot-check prompts (sample)

`aap-001` (en, in_distribution). Expected: walk the prohibition-strength hierarchy top-down (security-by-absence → deterministic prohibition at scaffolding). LoRA output: empty `<think></think>` (voice transferred), then a plausible-looking essay about putting rules in `.md` files instead of system prompts, ending with the same paragraph repeated three times in different headers. Keyword hits: 0/4. Decision pattern: not reached — answers a different question than asked.

`akc-001` (en, in_distribution). Expected: episode log must be append-only; mutation breaks reproducibility of distillation. LoRA output: empty `<think></think>`, then a discussion of "stored summaries as source of truth for the distillation pipeline" — directionally aligned but does not name `episode log`, `append-only`, or `immutable`; final paragraph rephrases the prior one. Keyword hits: 0/4.

`ca-001` (en, in_distribution). Expected: Emptiness — treat directives as contextually sensitive, not fixed; reflect on appropriateness rather than enforce strict adherence on a constitution that has begun to conflict with itself. LoRA output: empty `<think></think>`, then a hallucinated `contemplative` field in `constitution.md` invented from whole cloth. None of the four Contemplative axioms (Emptiness / Non-Duality / Mindfulness / Boundless Care) appear. Keyword hits: 0/4.

The pattern is consistent across the three lines spot-checked: **`<think>` collapse → fluent shimo4228-adjacent prose → framework absent → end-of-output repetition**. This is the Phase 0 mannerism wrapper at a stronger intensity (Phase 0 reported looping in "some" outputs; this run shows it in 84%).

## Decision

**Stage D verdict: FAIL**, recorded per the plan's early-stop rubric. Two corollary decisions follow.

### 1. Corpus deliverable is retained

`corpus/v0.1.0/{train,valid,pilot}.jsonl` and `manifest.json` stay as the deliverable for this version. The corpus is base-model-independent and was never gated on whether one specific 8B-4bit base under 300 iterations of LoRA could absorb judgment from it. The CLAUDE.md project pivot (corpus is primary, LoRA is derived side product) is exactly the policy that lets this verdict not destroy the artifact.

The corpus version is left at `v0.1.0`, but `manifest.json` is updated to mark `stage: "D"`, the new `train.jsonl` and `valid.jsonl` counts, and a `verification_lora_verdict` field recording the FAIL.

### 2. Stage E does not proceed under this verdict

Stage E (Zenodo deposit, HF mirror sync, hub back-propagation, `llms.txt`) is **not triggered** by this commit. The reason is not that the corpus is unfit for deposit, but that depositing v0.1.0 with `verification_lora_verdict: FAIL` invites the wrong reading — a casual reader of the hub `EcosystemRepo` row would assume the artifact was uncontroversially complete. The right shape is to either (a) deposit with an explicit "verification probe failed; corpus is the deliverable, training-time judgment transfer not yet demonstrated" framing in the README and CITATION.cff `description`, or (b) iterate one more turn before deposit.

Recommendation: defer the deposit decision until after the next session, where the trade-off between "deposit as preliminary record" vs "iterate on data scale / extractor shape first" can be made with the eval evidence in front of the author rather than in the middle of a long-running session.

## Alternatives considered

**Continue training to iter 400 and re-eval.** Rejected. Phase 0 disposition-lora trained 400 iter on 230 examples and produced the same mannerism wrapper pattern; we trained ~equivalent total token-touches on a 4-line corpus and produced a stronger version of the same pattern. The next 100 iterations on this base + this data would not flip an 84% loop rate to a <30% loop rate.

**Re-run eval against the iter 100 or iter 200 checkpoint.** Rejected for this ADR. The checkpoints exist (`0000100_adapters.safetensors`, `0000200_adapters.safetensors`) and are cheap to evaluate against, but the question they answer — "did the model already mannerism-wrap at iter 100, or did it develop the symptom later?" — belongs in a v0.2.0 ablation, not in the Stage D verdict for v0.1.0.

**Try a larger base model.** Out of scope for the Stage D plan and for the local hardware (16 GB Mac). A Qwen3-30B or Llama-70B target would shift the question from "does the corpus contain enough signal for an 8B base to absorb judgment" to "does any base absorb it from 851 examples", which is a different research question and properly belongs to a downstream lab.

**Quietly downgrade the verdict to MARGINAL and proceed.** Rejected. The plan's verdict rubric was written before the run; reading the rubric *after* the fact in a way that lets the verdict pass would defeat the early-stop gate's whole purpose.

## Consequences

### Immediate (this commit)

- `corpus/v0.1.0/manifest.json` records `stage: "D"`, refreshed counts, and a new `verification_lora_verdict` field
- `CHANGELOG.md` gains a Stage D entry under `[Unreleased]` documenting the FAIL with auto-signals
- `outputs/eval/compare.md`, `outputs/adapters/v0/*.safetensors`, and `outputs/logs/*.log` stay under `outputs/` (gitignored — `*.safetensors` and `outputs/` in `.gitignore`) and are not committed
- No Stage E deposit triggered

### For v0.2.0 (out of scope here, recorded as hypothesis)

Two non-exclusive hypotheses for why the 851-example corpus did not flip the Phase 0 verdict, ordered by my prior:

1. **Data scale.** The literature on instruction-tuning judgment transfer (Alpaca's 52 k, FLAN's millions, Stanford's pre-LIMA work) suggests 800–1000 examples is in the *voice-transfer regime*, not the *judgment-transfer regime*. The shape of the corpus may be correct (judgment-eliciting Q&A across four lines) and the only fix may be more pairs per ADR / more derived situations per glossary entry / contrast-shape pairs that the v0.1.0 plan explicitly left out.

2. **Shape distribution.** Of 851 pairs, 226 (27%) are judgment shape; the remaining 73% are zenn/adrs/glossary/thesis which are explain/definition shape near-verbatim from the source. The LoRA may have learned the dominant shape (explain — fluent shimo4228-adjacent prose) at the cost of the rare shape (judgment — apply framework, name the decision). The `meta.shape` field was added to the corpus precisely to enable this ablation; v0.2.0 should run shape-stratified LoRAs against `prompt_bank.yaml`.

Both hypotheses are testable; neither is testable inside Stage D's scope. The `meta.shape` structure already exists in the corpus to support hypothesis 2; the shape-stratified ablation is the natural next experiment.

### Process

The verification-LoRA-as-disposable-probe pattern worked as intended — it caught the failure mode before any deposit decision was made. The two-layer judgment validation (ADR-0004) caught nothing of this; the Layer 2 rubric agent validated judgment *pair quality* (the data was well-formed) but cannot predict whether well-formed data is sufficient for training-time judgment transfer at a given (data scale, base model, iteration budget) point. Stage D's verification LoRA is the only signal in this entire pipeline that catches the (scale × shape × base) interaction, and the cost of running it (~3 hours of probe training + eval on local hardware, plus the writing of this ADR) is a load-bearing investment, not overhead.
