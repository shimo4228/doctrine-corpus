"""Fire-alarm validator for Claude Code session-generated judgment.jsonl pairs.

This script is **Layer 1** of the two-layer validation gate defined in
[ADR-0004](../docs/adr/0004-rubric-based-semantic-judgment-validation.md).
It catches **structural and surface-pattern regressions only**. Semantic
quality (decision equivalence, framework application, K=2 facet diversity,
anti-mannerism) is judged by Layer 2 — the project-local Claude Code agent
at `doctrine-corpus/.claude/agents/judgment-pair-reviewer.md`.

Each pair is checked for:

1. **Schema** — meta has {line, source, lang, shape}, shape == "judgment",
   messages are non-empty.
2. **Q anti-chunk** — Q does not match chunk-as-completion regex patterns
   ("Zenn 記事を書い…", "ADR…を解説", "write an article", "explain ADR-…").
3. **Q novelty** — Q does not contain the first 200 characters of the
   source ADR's Context verbatim (prevents chunk-as-completion regression).

The vocabulary-frequency overlap check (`decision_drift_score`) and the
keyword-presence check (`has_framework_keyword`) that previous versions
of this script ran were **removed** in ADR-0004. Vocabulary overlap and
substring matching cannot measure judgment equivalence — that's the
rubric agent's job.

Trust boundary: generated content is untrusted
([`~/.claude/rules/common/security.md`](file://~/.claude/rules/common/security.md)).
The validator enforces meta field types and detects regression patterns
but does not sanitize message bodies — rubric review is the next gate.

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

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_ADRS = REPO_ROOT / "data" / "adrs.jsonl"

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
    """Return (judgment_prefix, context) from the generated Q text.

    Q format produced by the generator is `{prefix}\n\n{context}`. When no
    delimiter is present, the whole Q is treated as context.
    """
    parts = q.split("\n\n", 1)
    if len(parts) < 2:
        return q.strip(), ""
    return parts[0].strip(), parts[1].strip()


def load_source_lookup(adrs_path: Path) -> dict[str, str]:
    """Index data/adrs.jsonl judgment entries by (source_path, lang) → Context.

    Only the Context portion of the source ADR Q is retained; the Decision
    side is no longer used by this script (semantic comparison moved to the
    rubric agent).
    """
    index: dict[str, str] = {}
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
            _, context = split_judgment_q(q)
            if key not in index:
                index[key] = context
    return index


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
    source_lookup: dict[str, str],
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

    lang = meta.get("lang", "en")
    source = meta.get("source", "").split("#", 1)[0]
    src_key = f"{source}|{lang}"
    src_context = source_lookup.get(src_key, "")
    if not src_context:
        # Fallback: same source other lang
        for other_lang in ("en", "ja"):
            if other_lang == lang:
                continue
            alt = source_lookup.get(f"{source}|{other_lang}", "")
            if alt:
                src_context = alt
                break

    if q and src_context:
        if q_novelty_violation(q, src_context):
            failures.append("q_novelty:verbatim_200")

    if q:
        chunk_hit = q_anti_chunk_violation(q, lang)
        if chunk_hit:
            failures.append(f"q_anti_chunk:{chunk_hit}")

    return {
        "passed": not failures,
        "failures": failures,
        "meta": meta,
        "q_preview": q[:120],
        "a_preview": a[:120],
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Fire-alarm validator for data/judgment.jsonl. Catches structural "
            "and regex regressions only. For semantic quality, invoke the "
            "judgment-pair-reviewer Claude Code agent after this script passes."
        )
    )
    ap.add_argument("path", type=Path, help="Path to judgment.jsonl")
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

    results = [validate_entry(e, source_lookup) for e in entries]

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

    novelty_violations = sum(
        1 for r in results for f in r["failures"] if f.startswith("q_novelty")
    )
    novelty_rate = (n - novelty_violations) / n if n else 1.0

    print(f"Validated {n} entries from {args.path} (Layer 1: fire alarm)")
    if n:
        print(f"  PASS: {n_pass}  ({n_pass / n:.0%})")
        print(f"  FAIL: {n_fail}  ({n_fail / n:.0%})")
    else:
        print("  (no entries)")
    print()

    print("Per-line PASS / TOTAL:")
    for line in sorted(per_line_total):
        passed = per_line_pass.get(line, 0)
        total = per_line_total[line]
        print(f"  {line:25s} {passed:3d}/{total:3d}  ({passed / total:.0%})")
    print()

    print("Aggregate metrics:")
    print(f"  Q novelty rate:              {novelty_rate:.0%}")
    print()

    if failure_kinds:
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

    if n_pass == n and n > 0:
        print(
            "Next step: invoke the judgment-pair-reviewer agent for semantic "
            "validation (Layer 2). See ADR-0004."
        )


if __name__ == "__main__":
    main()
