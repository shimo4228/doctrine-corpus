"""Compare base model vs LoRA-adapted model on the doctrine-corpus prompt bank.

Generates a side-by-side Markdown report at outputs/eval/compare.md so the
human reviewer can apply the Stage D early-stop gate from the plan:

- auto signals: per-line keyword hit-rate, loop-detection counts
- hand-review: spot-check that LoRA outputs reach each prompt's
  expected_decision_pattern (12 prompts: in_distribution / generalization /
  cross_line × 4 lines)

The LoRA artifact is verification-only. See
docs/adr/0005-stage-d-verification-lora-result.md for the verdict and
base-model-lab/experiments/disposition-lora/findings.md for the Phase 0
precedent.

Usage:
    uv run python eval/eval_compare.py
    uv run python eval/eval_compare.py --lang en --line akc
    uv run python eval/eval_compare.py --model mlx-community/Qwen3-8B-4bit \
        --adapter ./outputs/adapters/v0
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_BANK = REPO_ROOT / "eval" / "prompt_bank.yaml"

LANG_CHOICES = ("en", "ja", "both")
LINE_CHOICES = ("akc", "aap", "authorship-strategy", "contemplative-agent", "all")


def load_prompt_bank(path: Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise SystemExit(
            f"prompt_bank.yaml not found: {path}\nPass --prompt-bank to override."
        ) from e
    data = yaml.safe_load(raw)
    prompts = data.get("prompts", []) if isinstance(data, dict) else []
    if not isinstance(prompts, list):
        raise ValueError(f"prompt_bank.yaml: expected list under 'prompts', got {type(prompts)}")
    return prompts


def filter_prompts(
    prompts: list[dict[str, Any]], line: str, lang: str
) -> list[tuple[str, str, str, dict[str, Any]]]:
    """Return [(id, lang, text, meta), ...] flattened across requested langs.

    meta carries: line, category, expected_framework_keywords, expected_decision_pattern.
    """
    langs = ("en", "ja") if lang == "both" else (lang,)
    out: list[tuple[str, str, str, dict[str, Any]]] = []
    for p in prompts:
        if line != "all" and p.get("line") != line:
            continue
        for lg in langs:
            text = p.get(lg)
            if not text:
                continue
            meta = {
                "line": p.get("line", "?"),
                "category": p.get("category", "?"),
                "expected_framework_keywords": p.get("expected_framework_keywords", []),
                "expected_decision_pattern": p.get("expected_decision_pattern", ""),
            }
            out.append((p.get("id", "?"), lg, text, meta))
    return out


def keyword_hit_rate(output: str, keywords: list[str]) -> tuple[int, int]:
    """Return (hits, total). Match case-insensitively; multi-word keywords are
    matched as whole substrings, single-word keywords with word boundaries."""
    if not keywords:
        return (0, 0)
    text = output.lower()
    hits = 0
    for kw in keywords:
        kw_l = kw.lower()
        if " " in kw_l or "-" in kw_l:
            if kw_l in text:
                hits += 1
        else:
            if re.search(rf"\b{re.escape(kw_l)}\b", text):
                hits += 1
    return (hits, len(keywords))


def detect_looping(output: str) -> bool:
    """Phase 0 regression signal: same 3-gram repeated 3+ times.

    Tokenization is whitespace-based for English; for Japanese we fall back to
    a sliding character window since whitespace tokenization is degenerate.
    Returns True if any 3-gram (token or 3-char) appears 3+ times.
    """
    if not output.strip():
        return False
    tokens = output.split()
    if len(tokens) >= 9:
        trigrams = [" ".join(tokens[i : i + 3]) for i in range(len(tokens) - 2)]
        counts = Counter(trigrams)
        if counts and counts.most_common(1)[0][1] >= 3:
            return True
    chars = "".join(output.split())
    if len(chars) >= 30:
        char_trigrams = [chars[i : i + 6] for i in range(len(chars) - 5)]
        counts = Counter(char_trigrams)
        if counts and counts.most_common(1)[0][1] >= 5:
            return True
    return False


def load_pair(model_id: str, adapter_path: Path | None) -> tuple[Any, Any]:
    """Lazy import + load. Returns (model, tokenizer). mlx_lm types are opaque
    at static-analysis time; Any is intentional binding-to-external-binary."""
    from mlx_lm import load  # type: ignore[import-not-found]

    if adapter_path is None:
        return load(model_id)
    return load(model_id, adapter_path=str(adapter_path))


def generate(model: Any, tokenizer: Any, prompt: str, max_tokens: int) -> str:
    from mlx_lm import generate as mlx_generate  # type: ignore[import-not-found]

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    return mlx_generate(model, tokenizer, prompt=text, max_tokens=max_tokens)


def _render_per_line_summary(rows: list[dict[str, Any]]) -> list[str]:
    by_line: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_line.setdefault(r["line"], []).append(r)
    out = ["## Per-line summary (LoRA auto signals)", ""]
    out.append("| line | prompts | mean keyword hit-rate | loop-detected count |")
    out.append("|---|---:|---:|---:|")
    for line, items in sorted(by_line.items()):
        n = len(items)
        rates = [r["lora_hit_rate"] for r in items if r["lora_kw_total"] > 0]
        mean_rate = sum(rates) / len(rates) if rates else 0.0
        loops = sum(1 for r in items if r["lora_loop"])
        out.append(f"| {line} | {n} | {mean_rate:.2f} | {loops} |")
    out.append("")
    overall_rates = [r["lora_hit_rate"] for r in rows if r["lora_kw_total"] > 0]
    overall_mean = sum(overall_rates) / len(overall_rates) if overall_rates else 0.0
    overall_loops = sum(1 for r in rows if r["lora_loop"])
    out.append(
        f"**Overall**: prompts={len(rows)}, mean keyword hit-rate={overall_mean:.2f}, "
        f"loop-detected={overall_loops}"
    )
    out.append("")
    return out


def render_report(
    model_id: str,
    adapter_path: Path,
    rows: list[dict[str, Any]],
    out: Path,
) -> None:
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    lines: list[str] = [
        "# doctrine-corpus Stage D — base vs LoRA comparison",
        "",
        f"- Generated: {timestamp}",
        f"- Base model: `{model_id}`",
        f"- Adapter: `{adapter_path}`",
        f"- Prompts evaluated: {len(rows)}",
        "",
        "Each prompt is run through (A) the base model and (B) the LoRA-adapted",
        "model. The early-stop gate (see Stage D plan) reads from:",
        "",
        "1. **Auto signals** — per-line keyword hit-rate (regex over",
        "   `expected_framework_keywords`) and loop-detection counts.",
        "2. **Hand-review** — judge whether LoRA reaches the prompt's",
        "   `expected_decision_pattern` on 12 spot-check prompts",
        "   (in_distribution / generalization / cross_line × 4 lines).",
        "",
    ]
    lines.extend(_render_per_line_summary(rows))
    lines.append("---")
    lines.append("")

    by_line: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_line.setdefault(r["line"], []).append(r)

    for line in sorted(by_line.keys()):
        lines.append(f"## Line: `{line}`")
        lines.append("")
        for r in by_line[line]:
            kw_hits, kw_total = r["lora_kw_hits"], r["lora_kw_total"]
            loop_flag = " [LOOP DETECTED]" if r["lora_loop"] else ""
            lines.extend(
                [
                    f"### {r['id']} ({r['lang']}, {r['category']}){loop_flag}",
                    "",
                    f"> {r['prompt']}",
                    "",
                    "**Rubric**:",
                    "",
                    f"- expected framework keywords: `{r['kw_list']}`",
                    f"- expected decision pattern: {r['decision_pattern']}",
                    f"- LoRA keyword hits: {kw_hits} / {kw_total}",
                    "",
                    "#### A. base",
                    "",
                    r["base_out"].strip() or "_(empty)_",
                    "",
                    "#### B. LoRA",
                    "",
                    r["lora_out"].strip() or "_(empty)_",
                    "",
                    "---",
                    "",
                ]
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen3-8B-4bit")
    ap.add_argument(
        "--adapter",
        type=Path,
        default=REPO_ROOT / "outputs" / "adapters" / "v0",
    )
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "outputs" / "eval" / "compare.md",
    )
    ap.add_argument("--lang", choices=LANG_CHOICES, default="both")
    ap.add_argument("--line", choices=LINE_CHOICES, default="all")
    ap.add_argument(
        "--prompt-bank",
        type=Path,
        default=PROMPT_BANK,
        help="Path to prompt_bank.yaml (default: eval/prompt_bank.yaml)",
    )
    args = ap.parse_args()

    prompts = load_prompt_bank(args.prompt_bank)
    selected = filter_prompts(prompts, line=args.line, lang=args.lang)
    if not selected:
        raise SystemExit(
            f"no prompts selected for --line={args.line} --lang={args.lang}"
        )
    print(f"selected {len(selected)} prompts (line={args.line}, lang={args.lang})")

    # Sequential load: 8B-4bit base + LoRA simultaneously would peak ~13 GB
    # resident on a 16 GB Mac, which observably wedges Metal under memory
    # pressure. Generate all base outputs first, free the model, then load
    # LoRA and generate again.
    import gc

    base_outs: list[str] = []
    print(f"phase 1/2 — loading base model: {args.model}")
    base_model, base_tok = load_pair(args.model, adapter_path=None)
    for i, (pid, lang, prompt, *_) in enumerate(selected, 1):
        print(f"[base {i}/{len(selected)}] {pid} ({lang})")
        base_outs.append(generate(base_model, base_tok, prompt, args.max_tokens))
    del base_model, base_tok
    gc.collect()

    lora_outs: list[str] = []
    print(f"phase 2/2 — loading LoRA-adapted model: {args.model} + {args.adapter}")
    lora_model, lora_tok = load_pair(args.model, adapter_path=args.adapter)
    for i, (pid, lang, prompt, *_) in enumerate(selected, 1):
        print(f"[lora {i}/{len(selected)}] {pid} ({lang})")
        lora_outs.append(generate(lora_model, lora_tok, prompt, args.max_tokens))
    del lora_model, lora_tok
    gc.collect()

    rows: list[dict[str, Any]] = []
    for (pid, lang, prompt, meta), base_out, lora_out in zip(
        selected, base_outs, lora_outs, strict=True
    ):
        kw_hits, kw_total = keyword_hit_rate(lora_out, meta["expected_framework_keywords"])
        rows.append(
            {
                "id": pid,
                "lang": lang,
                "line": meta["line"],
                "category": meta["category"],
                "prompt": prompt,
                "kw_list": meta["expected_framework_keywords"],
                "decision_pattern": meta["expected_decision_pattern"],
                "base_out": base_out,
                "lora_out": lora_out,
                "lora_kw_hits": kw_hits,
                "lora_kw_total": kw_total,
                "lora_hit_rate": (kw_hits / kw_total) if kw_total else 0.0,
                "lora_loop": detect_looping(lora_out),
            }
        )

    render_report(args.model, args.adapter, rows, args.out)
    print(f"wrote: {args.out}")


if __name__ == "__main__":
    main()
