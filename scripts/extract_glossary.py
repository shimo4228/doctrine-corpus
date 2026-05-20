"""Extract glossary entries from research lines into doctrine-corpus JSONL.

For each glossary file configured in `scripts/line_templates.yaml`, emits one
`shape: "definition"` example per H2 section. Q is built from the line's
`definition_prompt[lang]` with `{term}` and `{line_name}` substituted; A is
the section body verbatim.

Currently only the **section** parser is implemented. AKC and Contemplative
Agent glossaries are markdown translation tables, not concept definitions —
their `glossary_path` is set to `null` in the YAML and they are skipped here.
Their concept-level coverage is provided by ADR explain + judgment pairs.

Provenance: follows the same shape as `scripts/extract_adrs.py` (YAML loader,
EN/JA pass separation, `build_meta` helper, per-line counter, skip
classification). Heading parsing reuses the same regex idiom but treats H2
headings as **term names** rather than ADR sections.

Usage:
    python scripts/extract_glossary.py
    python scripts/extract_glossary.py --lines aap authorship-strategy
    python scripts/extract_glossary.py --templates scripts/line_templates.yaml \\
        --out data/glossary.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_TEMPLATES = REPO_ROOT / "scripts" / "line_templates.yaml"
DEFAULT_OUT = REPO_ROOT / "data" / "glossary.jsonl"

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
ASCII_PUNCT_RE = re.compile(r"[!-/:-@\[-`{-~]")


@dataclass(frozen=True)
class GlossaryEntry:
    term: str
    body: str
    slug: str


def strip_preamble(text: str) -> str:
    """Drop the language-toggle preamble (and anything before the H1)."""
    m = H1_RE.search(text)
    if not m:
        return text
    return text[m.end() :]


def split_sections(text: str) -> list[GlossaryEntry]:
    """Split a glossary body into H2 sections.

    The H2 heading text is used as the term name. Slug is derived by
    lowercasing, removing ASCII punctuation, and collapsing whitespace to
    hyphens. Non-ASCII characters (Japanese, etc.) are preserved in the slug.
    Duplicate slugs receive a numeric suffix.
    """
    matches = list(H2_RE.finditer(text))
    if not matches:
        return []

    entries: list[GlossaryEntry] = []
    seen_slugs: dict[str, int] = {}
    for i, m in enumerate(matches):
        term = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        base_slug = slugify(term)
        if base_slug in seen_slugs:
            seen_slugs[base_slug] += 1
            slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[base_slug] = 0
            slug = base_slug
        entries.append(GlossaryEntry(term=term, body=body, slug=slug))
    return entries


def slugify(term: str) -> str:
    no_punct = ASCII_PUNCT_RE.sub(" ", term)
    collapsed = re.sub(r"\s+", "-", no_punct.strip().lower())
    return collapsed or "term"


def parse_glossary(path: Path) -> list[GlossaryEntry]:
    text = path.read_text(encoding="utf-8")
    stripped = strip_preamble(text)
    return split_sections(stripped)


def build_meta(
    line: str, slug: str, lang: str, glossary_filename: str
) -> dict[str, Any]:
    return {
        "line": line,
        "source": f"docs/{glossary_filename}#{slug}",
        "lang": lang,
        "shape": "definition",
    }


def build_example(
    entry: GlossaryEntry,
    line_key: str,
    line_cfg: dict[str, Any],
    lang: str,
    glossary_filename: str,
) -> dict:
    prompt_template = line_cfg["definition_prompt"][lang]
    prompt = prompt_template.format(term=entry.term, line_name=line_cfg["name"])
    return {
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": entry.body},
        ],
        "meta": build_meta(
            line=line_key,
            slug=entry.slug,
            lang=lang,
            glossary_filename=glossary_filename,
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument(
        "--lines",
        nargs="*",
        default=None,
        help="Subset of line keys to process. Default: all lines in the YAML.",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    with args.templates.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    selected_lines: dict[str, dict[str, Any]] = config["lines"]
    if args.lines:
        selected_lines = {k: v for k, v in selected_lines.items() if k in args.lines}

    args.out.parent.mkdir(parents=True, exist_ok=True)

    written_total = 0
    per_line_counts: dict[str, dict[str, int]] = {}
    skipped_lines: list[str] = []

    with args.out.open("w", encoding="utf-8") as f:
        for line_key, line_cfg in selected_lines.items():
            glossary_en = line_cfg.get("glossary_path")
            glossary_ja = line_cfg.get("glossary_path_ja")
            if not glossary_en and not glossary_ja:
                skipped_lines.append(line_key)
                continue

            per_line_counts[line_key] = {"en": 0, "ja": 0}

            if glossary_en:
                en_path = Path(glossary_en)
                if not en_path.exists():
                    print(f"WARN: glossary_path missing for {line_key}: {en_path}")
                else:
                    entries = parse_glossary(en_path)
                    for entry in entries:
                        ex = build_example(
                            entry=entry,
                            line_key=line_key,
                            line_cfg=line_cfg,
                            lang="en",
                            glossary_filename=en_path.name,
                        )
                        f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        per_line_counts[line_key]["en"] += 1
                        written_total += 1

            if glossary_ja:
                ja_path = Path(glossary_ja)
                if not ja_path.exists():
                    print(f"WARN: glossary_path_ja missing for {line_key}: {ja_path}")
                else:
                    entries = parse_glossary(ja_path)
                    for entry in entries:
                        ex = build_example(
                            entry=entry,
                            line_key=line_key,
                            line_cfg=line_cfg,
                            lang="ja",
                            glossary_filename=ja_path.name,
                        )
                        f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        per_line_counts[line_key]["ja"] += 1
                        written_total += 1

    print("Per-line counts (glossary terms):")
    for line_key, counts in per_line_counts.items():
        total = counts["en"] + counts["ja"]
        print(
            f"  {line_key:25s} en={counts['en']:3d}  ja={counts['ja']:3d}  total={total:3d}"
        )

    if skipped_lines:
        print(
            f"Skipped lines (glossary_path null in YAML — translation tables, not concept definitions): "
            f"{', '.join(skipped_lines)}"
        )

    print(f"examples written: {written_total} -> {args.out}")


if __name__ == "__main__":
    main()
