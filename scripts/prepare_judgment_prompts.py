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
import re
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


# Boilerplate H3 headers that the parser must ignore. These are stylistic
# closers used across ADRs ("### What does not change", "### What stays the
# same") and carry no decision content — including them would dilute the
# K=2 facet-diversity hint.
_BOILERPLATE_H3_RE = re.compile(
    r"^\s*what\s+(does\s+not\s+change|stays\s+the\s+same)\b",
    re.IGNORECASE,
)
_H3_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
# All bold markers (`**`) are stripped from titles before they reach the
# user_prompt hint. The hint is consumed as plain prose; preserving markdown
# emphasis adds no value and a character-set ``strip("*")`` would leak a
# trailing `**` for inline-bold patterns like ``**Title.** Rest of sentence.``
# (the failure mode observed on AKC ADR-0008 / ADR-0011 numbered Decisions).
_BOLD_RE = re.compile(r"\*\*")
_SUB_ELEMENT_THRESHOLD = 3


def _strip_title(raw: str) -> str:
    """Normalise a sub-element title for the user_prompt facet-diversity hint.

    Removes ``**`` bold markers globally (handles both whole-title wrap and
    inline bold-prefix patterns) and trims surrounding whitespace.
    """
    return _BOLD_RE.sub("", raw).strip()


def extract_sub_elements(decision: str) -> list[str]:
    """Detect numbered or H3 sub-elements in an ADR Decision section.

    Returns the list of sub-element titles. Empty list when no clear
    sub-element structure exists (singleton decision).

    Detection priority:
      1. H3 sub-headers (``### Title``). Filters out boilerplate closers
         like "### What does not change" / "### What stays the same".
         Returns the surviving titles when 3 or more remain.
      2. Top-level numbered list (``1. Title``, ``2. Title`` ...).
         Returns the matched titles when 3 or more appear.
      3. Otherwise: returns ``[]`` (singleton). The user_prompt then omits
         the facet-diversity hint.

    Stripping note: leading/trailing ``**`` bold markers around the entire
    title are removed so the hint reads cleanly; emphasis *inside* the
    title is preserved.
    """
    if not decision:
        return []

    h3_titles = [_strip_title(m) for m in _H3_RE.findall(decision)]
    h3_substantive = [t for t in h3_titles if not _BOILERPLATE_H3_RE.match(t)]
    if len(h3_substantive) >= _SUB_ELEMENT_THRESHOLD:
        return h3_substantive

    # Numbered-list fallback fires ONLY when no substantive H3 structure
    # exists at all. Otherwise the numbered list belongs to the body of
    # an H3 (e.g. ADR-0012 H3 #1's inner four-paragraph plan) and we
    # must not promote it above the outer H3 hierarchy.
    if h3_substantive:
        return []

    numbered_titles = [
        _strip_title(title) for _, title in _NUMBERED_RE.findall(decision)
    ]
    if len(numbered_titles) >= _SUB_ELEMENT_THRESHOLD:
        return numbered_titles

    return []


def _parse_adr_number(adr_source: str) -> str | None:
    """Extract the 4-digit ADR number from a ``meta.source`` path.

    ``docs/adr/0001-core-adapter-separation.md#decision`` → ``"0001"``.
    Returns ``None`` when no recognizable ADR number is present (the
    caller should fall back to the default prefix variant).
    """
    match = re.search(r"adr/(\d{4})\b", adr_source)
    return match.group(1) if match else None


def select_judgment_prefix(
    line_cfg: dict[str, Any],
    adr_source: str,
    lang: str,
) -> str:
    """Return the judgment_prefix string for a given line config + ADR + lang.

    Supports two schemas in ``scripts/line_templates.yaml`` simultaneously:

    - **Legacy (akc / aap / authorship-strategy)**: ``judgment_prefix: {en, ja}``.
      Returns ``judgment_prefix[lang]`` directly.
    - **Variant-aware (contemplative-agent)**: ``judgment_prefix: {axiom, structural}.{en, ja}``
      + ``structural_adrs: [<4-digit ADR number>, ...]``. The ADR number is
      parsed out of ``adr_source``; if it appears in ``structural_adrs``, the
      ``structural`` variant is returned, otherwise the ``axiom`` variant.

    Defensive fallbacks: if the new schema is present but ``structural_adrs``
    is missing or the ADR number is unparseable, the ``axiom`` variant is
    returned (preserves Round 1 behavior for unclassified ADRs).

    **Asymmetry with `extract_adrs.py`**: that script (which builds the static
    `data/adrs.jsonl` source pairs) intentionally always uses the ``axiom``
    variant when it sees the variant-aware schema. This function is meant for
    *synthesis-prompt construction* and is the only place per-ADR ``structural``
    routing happens. Do not import this function into `extract_adrs.py` — the
    duplication is deliberate to keep `adrs.jsonl` free of per-ADR
    framing-prefix variance (the rubric's Bilingual Pair Equivalence check
    would flag mismatched EN/JA framings if both schemas leaked there).
    """
    prefix_cfg = line_cfg["judgment_prefix"]

    # Schema discrimination: variant-aware schema is indicated by the presence
    # of the "axiom" key (the default variant). Flat schema has language keys
    # directly. Distinguishing by *axiom-key presence* rather than *lang-key
    # presence* avoids a partially-populated flat schema (e.g. only "en")
    # falling through to the variant-aware branch and raising KeyError.
    if "axiom" not in prefix_cfg:
        # Legacy flat schema: {en, ja}
        return prefix_cfg[lang]

    # Variant-aware schema: {axiom, structural}.{en, ja}
    structural_adrs = set(line_cfg.get("structural_adrs", []) or [])
    adr_number = _parse_adr_number(adr_source)
    variant = "structural" if adr_number and adr_number in structural_adrs else "axiom"
    return prefix_cfg[variant][lang]


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
        f"If the source Decision contains multiple numbered or sub-headed "
        f"elements, the {k} alternative pairs MUST engage DIFFERENT elements "
        f"as their primary reasoning anchor — do not collapse them onto the "
        f"same element.\n\n"
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
    judgment_framing: str | None = None,
    sub_elements: list[str] | None = None,
) -> str:
    lang_full = LANG_FULL_NAME.get(lang, lang)
    few_shot_block = (
        format_few_shot(few_shot)
        if few_shot is not None
        else "(no few-shot pair available for this line; follow the rules strictly)"
    )

    framing_block = (
        f"Judgment framing for this ADR (use this lens when shaping each Q "
        f"and grounding each A):\n{judgment_framing.strip()}\n\n"
        if judgment_framing
        else ""
    )

    if sub_elements:
        enumerated = "\n".join(
            f"  {i + 1}. {title}" for i, title in enumerate(sub_elements)
        )
        sub_element_block = (
            f"The source Decision contains {len(sub_elements)} sub-elements "
            f"(facets that the {k} alternatives MUST span):\n{enumerated}\n\n"
            f"Each of the {k} alternatives MUST anchor on a DIFFERENT "
            f"sub-element from the list above. Pick sub-elements that are "
            f"conceptually distinct, not consecutive restatements of the "
            f"same facet.\n\n"
        )
    else:
        sub_element_block = ""

    return (
        f"Source ADR: {adr_source}\n\n"
        f"{framing_block}"
        f"Original Context:\n{context}\n\n"
        f"Original Decision (DO NOT CHANGE this — your generated pairs must "
        f"reach a logically equivalent Decision):\n{decision}\n\n"
        f"{sub_element_block}"
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
            judgment_framing = select_judgment_prefix(
                line_cfg, adr_source=adr_source, lang=lang
            )
            sub_elements = extract_sub_elements(decision)

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
                judgment_framing=judgment_framing,
                sub_elements=sub_elements,
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
                "sub_elements": sub_elements,
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
