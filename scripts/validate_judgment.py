"""Validate Claude Code session-generated judgment.jsonl pairs.

Each pair must pass five checks:

1. **Schema** — meta has {line, source, lang, shape}, shape == "judgment".
2. **Decision drift** — content tokens from the source ADR's Decision section
   appear in the generated A with >=50% coverage. Source Decision is looked
   up from `data/adrs.jsonl` by meta.source path (stripping any #fragment).
3. **Framework keyword** — at least one of the line's
   `judgment_synthesis_framework_keywords` appears in the generated A.
4. **Q novelty** — the generated Q does not contain the first 200 characters
   of the source ADR's Context verbatim (prevents chunk-as-completion regression).
5. **Q anti-chunk** — the Q does not use chunk-as-completion phrasing patterns
   ("Zenn 記事を書い…", "ADR…を解説", "write an article", "explain ADR-").

The checks are intentionally coarse — Stage D's `eval_compare.py` will run
the full semantic comparison. validate_judgment.py is the round-by-round
gate during Claude Code session-mediated generation.

Trust boundary: generated content is untrusted (rules/common/security.md).
The validator enforces meta field types and detects regression patterns
but does not sanitize message bodies — hand-review is the gate.

Usage:
    python scripts/validate_judgment.py data/judgment.jsonl
    python scripts/validate_judgment.py data/judgment.jsonl --tail 40
    python scripts/validate_judgment.py data/judgment.jsonl --top-fail 20
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_TEMPLATES = REPO_ROOT / "scripts" / "line_templates.yaml"
DEFAULT_ADRS = REPO_ROOT / "data" / "adrs.jsonl"

EN_WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z\-]{3,}\b")
JA_RUN_RE = re.compile(r"[一-龯ぁ-んァ-ヶー]{4,}")

ANTI_CHUNK_PATTERNS_EN = [
    re.compile(r"\bwrite an? article\b", re.IGNORECASE),
    re.compile(r"\bwrite a Zenn article\b", re.IGNORECASE),
    re.compile(r"\bexplain ADR-?\d+\b", re.IGNORECASE),
    re.compile(r"\bexplain the (?:above )?ADR\b", re.IGNORECASE),
]
ANTI_CHUNK_PATTERNS_JA = [
    re.compile(r"Zenn 記事を書"),
    re.compile(r"記事を書い"),
    re.compile(r"ADR[- ]?\d+\s*を解説"),
    re.compile(r"ADR\s*を解説"),
]

REQUIRED_META_KEYS = ("line", "source", "lang", "shape")


def split_judgment_q(q: str) -> tuple[str, str]:
    parts = q.split("\n\n", 1)
    if len(parts) < 2:
        return q.strip(), ""
    return parts[0].strip(), parts[1].strip()


def extract_decision(a: str) -> str:
    marker = "## Decision"
    if marker not in a:
        return a.strip()
    after_decision = a.split(marker, 1)[1].lstrip("\n").strip()
    if "\n## " in after_decision:
        after_decision = after_decision.split("\n## ", 1)[0].rstrip()
    return after_decision


def load_source_lookup(adrs_path: Path) -> dict[str, dict[str, str]]:
    """Index adrs.jsonl judgment entries by (source_path, lang) → {context, decision}."""
    index: dict[str, dict[str, str]] = {}
    if not adrs_path.exists():
        return index
    with adrs_path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError as e:
                print(
                    f"WARN: skipping malformed line {line_no} in {adrs_path}: {e}",
                    file=sys.stderr,
                )
                continue
            meta = entry.get("meta", {})
            if meta.get("shape") != "judgment":
                continue
            source = meta.get("source", "").split("#", 1)[0]
            lang = meta.get("lang", "")
            key = f"{source}|{lang}"
            messages = entry.get("messages", [])
            if len(messages) < 2:
                continue
            q = messages[0].get("content", "") if isinstance(messages[0], dict) else ""
            a = messages[1].get("content", "") if isinstance(messages[1], dict) else ""
            _, context = split_judgment_q(q)
            decision = extract_decision(a)
            if key not in index:
                index[key] = {"context": context, "decision": decision}
    return index


def extract_content_tokens(text: str, top_n: int = 10) -> set[str]:
    """Return up to `top_n` most-frequent content tokens (length >= 4)."""
    en = EN_WORD_RE.findall(text.lower())
    ja = JA_RUN_RE.findall(text)
    tokens = en + ja
    most_common = [tok for tok, _ in Counter(tokens).most_common(top_n)]
    return set(most_common)


def decision_drift_score(source_decision: str, generated_a: str) -> tuple[float, set[str]]:
    """Return (coverage_ratio, missing_tokens)."""
    source_tokens = extract_content_tokens(source_decision, top_n=10)
    if not source_tokens:
        return 1.0, set()
    gen_lower = generated_a.lower()
    found = {t for t in source_tokens if t.lower() in gen_lower or t in generated_a}
    missing = source_tokens - found
    ratio = len(found) / len(source_tokens)
    return ratio, missing


def has_framework_keyword(generated_a: str, keywords: list[str]) -> tuple[bool, str | None]:
    for kw in keywords:
        if kw.lower() in generated_a.lower():
            return True, kw
    return False, None


def q_anti_chunk_violation(q: str, lang: str) -> str | None:
    patterns = ANTI_CHUNK_PATTERNS_EN if lang == "en" else ANTI_CHUNK_PATTERNS_JA
    for p in patterns:
        if p.search(q):
            return p.pattern
    return None


def q_novelty_violation(q: str, source_context: str, window: int = 200) -> bool:
    if not source_context:
        return False
    prefix = source_context[:window].strip()
    if len(prefix) < 50:
        return False
    return prefix in q


def validate_entry(
    entry: dict[str, Any],
    source_lookup: dict[str, dict[str, str]],
    framework_keywords_by_line: dict[str, list[str]],
) -> dict[str, Any]:
    """Return per-entry validation result with PASS/FAIL flags and reasons."""
    failures: list[str] = []
    meta = entry.get("meta", {}) if isinstance(entry, dict) else {}

    for key in REQUIRED_META_KEYS:
        if key not in meta:
            failures.append(f"schema:missing_meta:{key}")
    if meta.get("shape") and meta.get("shape") != "judgment":
        failures.append(f"schema:wrong_shape:{meta.get('shape')}")

    messages = entry.get("messages", []) if isinstance(entry, dict) else []
    q = (
        messages[0].get("content", "")
        if len(messages) > 0 and isinstance(messages[0], dict)
        else ""
    )
    a = (
        messages[1].get("content", "")
        if len(messages) > 1 and isinstance(messages[1], dict)
        else ""
    )

    if not q or not a:
        failures.append("schema:empty_messages")

    line = meta.get("line", "")
    lang = meta.get("lang", "en")
    source = meta.get("source", "").split("#", 1)[0]
    src_key = f"{source}|{lang}"
    src = source_lookup.get(src_key)
    if not src:
        # Fallback: same source other lang
        for other_lang in ("en", "ja"):
            if other_lang == lang:
                continue
            alt_src = source_lookup.get(f"{source}|{other_lang}")
            if alt_src:
                src = alt_src
                break

    drift_ratio = 1.0
    missing_tokens: set[str] = set()
    if src and a:
        drift_ratio, missing_tokens = decision_drift_score(src["decision"], a)
        if drift_ratio < 0.5:
            failures.append(f"drift:{drift_ratio:.2f}")

    kw_ok = True
    kw_match: str | None = None
    keywords = framework_keywords_by_line.get(line, [])
    if a and keywords:
        kw_ok, kw_match = has_framework_keyword(a, keywords)
        if not kw_ok:
            failures.append("framework:none")

    if q and src:
        if q_novelty_violation(q, src["context"]):
            failures.append("q_novelty:verbatim_200")

    if q:
        chunk_hit = q_anti_chunk_violation(q, lang)
        if chunk_hit:
            failures.append(f"q_anti_chunk:{chunk_hit}")

    return {
        "passed": not failures,
        "failures": failures,
        "drift_ratio": drift_ratio,
        "missing_tokens": list(missing_tokens),
        "framework_match": kw_match,
        "meta": meta,
        "q_preview": q[:120],
        "a_preview": a[:120],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path, help="Path to judgment.jsonl")
    ap.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument("--adrs", type=Path, default=DEFAULT_ADRS)
    ap.add_argument(
        "--tail", type=int, default=None, help="Validate only the last N entries"
    )
    ap.add_argument(
        "--top-fail", type=int, default=10, help="Show top N failed entries"
    )
    args = ap.parse_args()

    if not args.path.exists():
        print(f"ERROR: {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    with args.templates.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    framework_keywords_by_line: dict[str, list[str]] = {
        line_key: cfg.get("judgment_synthesis_framework_keywords", [])
        for line_key, cfg in config["lines"].items()
    }

    source_lookup = load_source_lookup(args.adrs)

    all_entries: list[dict[str, Any]] = []
    parse_errors: list[tuple[int, str]] = []
    with args.path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            try:
                all_entries.append(json.loads(raw))
            except json.JSONDecodeError as e:
                parse_errors.append((line_no, str(e)))

    if parse_errors:
        print(f"JSONL parse errors ({len(parse_errors)} line(s)):", file=sys.stderr)
        for line_no, msg in parse_errors[:10]:
            print(f"  line {line_no}: {msg}", file=sys.stderr)

    entries = all_entries[-args.tail :] if args.tail else all_entries

    results = [
        validate_entry(e, source_lookup, framework_keywords_by_line) for e in entries
    ]

    n = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    n_fail = n - n_pass

    per_line_pass: dict[str, int] = {}
    per_line_total: dict[str, int] = {}
    for r in results:
        line = r["meta"].get("line", "unknown")
        per_line_total[line] = per_line_total.get(line, 0) + 1
        if r["passed"]:
            per_line_pass[line] = per_line_pass.get(line, 0) + 1

    failure_kinds: Counter[str] = Counter()
    for r in results:
        for f_str in r["failures"]:
            kind = f_str.split(":", 1)[0]
            failure_kinds[kind] += 1

    drift_ratios = [r["drift_ratio"] for r in results if r["meta"].get("line")]
    avg_drift = (
        sum(drift_ratios) / len(drift_ratios) if drift_ratios else 0.0
    )
    framework_inclusion = (
        sum(1 for r in results if r["framework_match"]) / n if n else 0.0
    )
    novelty_violations = sum(
        1 for r in results for f in r["failures"] if f.startswith("q_novelty")
    )
    novelty_rate = (n - novelty_violations) / n if n else 1.0

    print(f"Validated {n} entries from {args.path}")
    print(f"  PASS: {n_pass}  ({n_pass / n:.0%})" if n else "  (no entries)")
    print(f"  FAIL: {n_fail}  ({n_fail / n:.0%})" if n else "")
    print()

    print("Per-line PASS / TOTAL:")
    for line in sorted(per_line_total):
        passed = per_line_pass.get(line, 0)
        total = per_line_total[line]
        print(f"  {line:25s} {passed:3d}/{total:3d}  ({passed / total:.0%})")
    print()

    print("Aggregate metrics:")
    print(f"  Avg Decision-token coverage: {avg_drift:.2f}")
    print(f"  Framework keyword inclusion: {framework_inclusion:.0%}")
    print(f"  Q novelty rate:              {novelty_rate:.0%}")
    print()

    print("Failure kinds:")
    for kind, count in failure_kinds.most_common():
        print(f"  {kind:20s} {count}")
    print()

    failed = [r for r in results if not r["passed"]]
    if failed and args.top_fail > 0:
        print(f"Top {min(args.top_fail, len(failed))} failed entries:")
        for r in failed[: args.top_fail]:
            meta = r["meta"]
            print(
                f"  - line={meta.get('line', '?')} lang={meta.get('lang', '?')} "
                f"source={meta.get('source', '?')}"
            )
            print(f"    failures: {r['failures']}")
            print(f"    Q: {r['q_preview']}")
            print(f"    A: {r['a_preview']}")
            print()


if __name__ == "__main__":
    main()
