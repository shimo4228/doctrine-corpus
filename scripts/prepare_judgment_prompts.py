"""Prepare judgment Q&A synthesis prompts for Claude Code session-mediated generation.

Reads `data/adrs.jsonl`, filters `shape: "judgment"` entries, and builds one
prompt template per ADR per language into `data/judgment_prompts.jsonl`.
This script does **not** call any LLM. The intended workflow is:

    1. python scripts/prepare_judgment_prompts.py
    2. (Claude Code session reads the prompts, generates K=2 alternative
       judgment Q&A pairs per entry, appends them to data/judgment.jsonl)
    3. python scripts/validate_judgment.py data/judgment.jsonl

The session-mediated approach is preferred because shimo4228 operates under
a Claude Max plan; calling the Anthropic SDK would incur metered cost on
top of an already-flat subscription, and add an API key management surface.
The script's job is to construct everything the session needs (system
prompt, user prompt, source Decision for drift-checking, framework
keywords) and emit it as a structured JSONL artifact.

Each output entry carries:
  - adr_source: docs/adr/...md (repo-relative)
  - line, lang: same shape as the corpus meta fields
  - k: number of alternative pairs to generate (default 2)
  - system_prompt: corpus-extraction role instructions
  - user_prompt: framework, few-shot, original ADR, generation instructions
  - source_decision: ADR Decision verbatim (validate_judgment.py uses this)
  - framework_keywords: list of phrases the generated A must include >=1 of

Usage:
    python scripts/prepare_judgment_prompts.py
    python scripts/prepare_judgment_prompts.py --k 1
    python scripts/prepare_judgment_prompts.py --lines aap authorship-strategy
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_TEMPLATES = REPO_ROOT / "scripts" / "line_templates.yaml"
DEFAULT_ADRS = REPO_ROOT / "data" / "adrs.jsonl"
DEFAULT_PILOT = REPO_ROOT / "corpus" / "v0.1.0" / "pilot.jsonl"
DEFAULT_OUT = REPO_ROOT / "data" / "judgment_prompts.jsonl"

LANG_FULL_NAME = {"en": "English", "ja": "Japanese"}


def split_judgment_q(q: str) -> tuple[str, str]:
    """Return (judgment_prefix, context) from an adrs.jsonl judgment Q.

    The Q is assembled by extract_adrs.py as `{prefix}\\n\\n{context}` with a
    single-line prefix, so splitting on the first blank line is sufficient.
    """
    parts = q.split("\n\n", 1)
    if len(parts) < 2:
        return q.strip(), ""
    return parts[0].strip(), parts[1].strip()


def extract_decision(a: str) -> str:
    """Return the Decision section text from an adrs.jsonl judgment A.

    The A is assembled as `## Decision\\n\\n{decision}[\\n\\n## Consequences\\n\\n...]`.
    """
    marker = "## Decision"
    if marker not in a:
        return a.strip()
    after_decision = a.split(marker, 1)[1].lstrip("\n").strip()
    # Strip a trailing ## Consequences (or any other H2) block.
    if "\n## " in after_decision:
        after_decision = after_decision.split("\n## ", 1)[0].rstrip()
    return after_decision


def load_pilot_few_shot(pilot_path: Path) -> dict[tuple[str, str], dict]:
    """Index pilot.jsonl judgment pairs by (line, lang).

    Used as few-shot examples in the user prompt. Returns the first pair
    found per (line, lang) key.
    """
    indexed: dict[tuple[str, str], dict] = {}
    if not pilot_path.exists():
        return indexed
    with pilot_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            meta = entry.get("meta", {})
            if meta.get("shape") != "judgment":
                continue
            key = (meta.get("line", ""), meta.get("lang", ""))
            if key not in indexed:
                indexed[key] = entry
    return indexed


def pick_few_shot(
    line: str, lang: str, pilot_index: dict[tuple[str, str], dict]
) -> dict | None:
    """Pick a few-shot pair preferring (line, lang) → (any line, lang) → None."""
    if (line, lang) in pilot_index:
        return pilot_index[(line, lang)]
    for (_, other_lang), entry in pilot_index.items():
        if other_lang == lang:
            return entry
    return None


def format_few_shot(entry: dict) -> str:
    user_text = entry["messages"][0]["content"]
    assistant_text = entry["messages"][1]["content"]
    return (
        "{\n"
        f'  "messages": [\n'
        f'    {{"role": "user", "content": {json.dumps(user_text, ensure_ascii=False)}}},\n'
        f'    {{"role": "assistant", "content": {json.dumps(assistant_text, ensure_ascii=False)}}}\n'
        f"  ]\n"
        "}"
    )


def build_system_prompt(
    line_name: str, k: int, framework_keywords: list[str]
) -> str:
    keywords_display = ", ".join(framework_keywords)
    return (
        f"You are a corpus extraction tool for doctrine-corpus. "
        f"Given an Architecture Decision Record from {line_name}, generate {k} "
        f"alternative judgment-eliciting Q&A pairs that elicit the SAME Decision "
        f"through DIFFERENT situation entry points.\n\n"
        f"Each pair MUST:\n"
        f"1. State a NEW situation in the Q that is plausible for {line_name} "
        f"users to encounter (not the original ADR Context).\n"
        f"2. Apply the {line_name} framework explicitly in the A, naming at "
        f"least one of: {keywords_display}.\n"
        f"3. Reach a Decision logically equivalent to the source ADR's Decision.\n\n"
        f"Each pair MUST NOT:\n"
        f"- Introduce framework concepts not present in the source ADR.\n"
        f"- Change the Decision.\n"
        f"- Copy the original Context verbatim (no shared 30-word substring).\n"
        f'- Use chunk-as-completion phrasing ("write a Zenn article titled X", '
        f'"explain ADR-NNNN").\n\n'
        f'Output format: JSON list of {{"messages": [{{"role": "user", '
        f'"content": ...}}, {{"role": "assistant", "content": ...}}]}} — '
        f"exactly {k} entries. The target language is specified in the user "
        f"prompt; default to English when unspecified."
    )


def build_user_prompt(
    adr_source: str,
    context: str,
    decision: str,
    lang: str,
    few_shot: dict | None,
    k: int,
) -> str:
    lang_full = LANG_FULL_NAME.get(lang, lang)
    few_shot_block = (
        format_few_shot(few_shot)
        if few_shot is not None
        else "(no few-shot pair available for this line; follow the rules strictly)"
    )
    return (
        f"Source ADR: {adr_source}\n\n"
        f"Original Context:\n{context}\n\n"
        f"Original Decision (DO NOT CHANGE this — your generated pairs must "
        f"reach a logically equivalent Decision):\n{decision}\n\n"
        f"Few-shot example (existing judgment pair from doctrine-corpus, "
        f"target language: {lang}):\n{few_shot_block}\n\n"
        f"Now generate {k} alternative judgment-eliciting Q&A pairs in "
        f"{lang_full}, following the rules in the system prompt. "
        f"Output JSON only, no commentary."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument("--adrs", type=Path, default=DEFAULT_ADRS)
    ap.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--lines",
        nargs="*",
        default=None,
        help="Subset of line keys to process. Default: all judgment ADRs in adrs.jsonl.",
    )
    ap.add_argument("--k", type=int, default=2)
    args = ap.parse_args()

    with args.templates.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    line_configs: dict[str, dict[str, Any]] = config["lines"]

    pilot_index = load_pilot_few_shot(args.pilot)

    args.out.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped_no_decision = 0
    per_line_counts: dict[str, dict[str, int]] = {}

    with args.adrs.open(encoding="utf-8") as src, args.out.open(
        "w", encoding="utf-8"
    ) as dst:
        for raw in src:
            if not raw.strip():
                continue
            entry = json.loads(raw)
            meta = entry.get("meta", {})
            if meta.get("shape") != "judgment":
                continue

            line_key = meta.get("line", "")
            if args.lines and line_key not in args.lines:
                continue
            if line_key not in line_configs:
                continue

            lang = meta.get("lang", "en")
            line_cfg = line_configs[line_key]
            line_name = line_cfg["name"]
            framework_keywords = line_cfg.get(
                "judgment_synthesis_framework_keywords", []
            )

            q = entry["messages"][0]["content"]
            a = entry["messages"][1]["content"]
            _, context = split_judgment_q(q)
            decision = extract_decision(a)

            if not context or not decision:
                skipped_no_decision += 1
                continue

            few_shot = pick_few_shot(line_key, lang, pilot_index)
            adr_source = meta.get("source", "").split("#", 1)[0]

            system_prompt = build_system_prompt(
                line_name=line_name, k=args.k, framework_keywords=framework_keywords
            )
            user_prompt = build_user_prompt(
                adr_source=adr_source,
                context=context,
                decision=decision,
                lang=lang,
                few_shot=few_shot,
                k=args.k,
            )

            out_entry = {
                "adr_source": adr_source,
                "line": line_key,
                "lang": lang,
                "k": args.k,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "source_decision": decision,
                "framework_keywords": framework_keywords,
            }
            dst.write(json.dumps(out_entry, ensure_ascii=False) + "\n")
            written += 1

            stats = per_line_counts.setdefault(
                line_key, {"en": 0, "ja": 0}
            )
            stats[lang] = stats.get(lang, 0) + 1

    print("Per-line prompt counts:")
    for line_key, counts in per_line_counts.items():
        en = counts.get("en", 0)
        ja = counts.get("ja", 0)
        print(
            f"  {line_key:25s} en={en:3d}  ja={ja:3d}  total={en + ja:3d}"
        )

    print(f"Skipped (no Context or Decision): {skipped_no_decision}")
    print(
        f"prompts written: {written} (each will produce K={args.k} pairs) "
        f"-> {args.out}"
    )
    print(f"Expected judgment.jsonl size after full generation: {written * args.k}")


if __name__ == "__main__":
    main()
