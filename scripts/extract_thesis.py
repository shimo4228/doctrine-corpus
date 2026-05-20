"""Extract thesis sections from research lines into doctrine-corpus JSONL.

For each thesis file configured in `scripts/line_templates.yaml`, emits one
`shape: "explain"` example per H2 section. Q is built from the line's
`thesis_explain_prompt[lang]` with `{section_title}` and `{line_name}`
substituted; A is the section body verbatim (including any H3 subsections,
since the section's argumentative weight depends on its internal structure).

Only AAP and Authorship Strategy have thesis files; AKC and Contemplative
Agent have `thesis_path: null` in the YAML and are skipped.

Provenance: parallels `scripts/extract_glossary.py` (YAML loader, EN/JA pass
separation, `build_meta` helper, per-line counter). Heading parsing reuses
the H2 split idiom but treats the section as an *exposition unit*, not a
*term definition*.

Usage:
    python scripts/extract_thesis.py
    python scripts/extract_thesis.py --lines aap
    python scripts/extract_thesis.py --templates scripts/line_templates.yaml \\
        --out data/thesis.jsonl
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
DEFAULT_OUT = REPO_ROOT / "data" / "thesis.jsonl"

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
ASCII_PUNCT_RE = re.compile(r"[!-/:-@\[-`{-~]")


@dataclass(frozen=True)
class ThesisSection:
    title: str
    body: str
    slug: str


def strip_preamble(text: str) -> str:
    """Drop the language-toggle preamble and pull-quote (anything before H1)."""
    m = H1_RE.search(text)
    if not m:
        return text
    return text[m.end() :]


def slugify(title: str) -> str:
    no_punct = ASCII_PUNCT_RE.sub(" ", title)
    collapsed = re.sub(r"\s+", "-", no_punct.strip().lower())
    return collapsed or "section"


def split_sections(text: str) -> list[ThesisSection]:
    """Split a thesis body into H2 sections, preserving any H3 subsections."""
    matches = list(H2_RE.finditer(text))
    if not matches:
        return []

    sections: list[ThesisSection] = []
    seen_slugs: dict[str, int] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        base_slug = slugify(title)
        if base_slug in seen_slugs:
            seen_slugs[base_slug] += 1
            slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[base_slug] = 0
            slug = base_slug
        sections.append(ThesisSection(title=title, body=body, slug=slug))
    return sections


def parse_thesis(path: Path) -> list[ThesisSection]:
    text = path.read_text(encoding="utf-8")
    stripped = strip_preamble(text)
    return split_sections(stripped)


def build_meta(
    line: str, slug: str, lang: str, thesis_filename: str
) -> dict[str, Any]:
    return {
        "line": line,
        "source": f"docs/{thesis_filename}#{slug}",
        "lang": lang,
        "shape": "explain",
    }


def build_example(
    section: ThesisSection,
    line_key: str,
    line_cfg: dict[str, Any],
    lang: str,
    thesis_filename: str,
) -> dict:
    prompt_template = line_cfg["thesis_explain_prompt"][lang]
    prompt = prompt_template.format(
        section_title=section.title, line_name=line_cfg["name"]
    )
    return {
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": section.body},
        ],
        "meta": build_meta(
            line=line_key,
            slug=section.slug,
            lang=lang,
            thesis_filename=thesis_filename,
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
            thesis_en = line_cfg.get("thesis_path")
            thesis_ja = line_cfg.get("thesis_path_ja")
            if not thesis_en and not thesis_ja:
                skipped_lines.append(line_key)
                continue

            per_line_counts[line_key] = {"en": 0, "ja": 0}

            if thesis_en:
                en_path = Path(thesis_en)
                if not en_path.exists():
                    print(f"WARN: thesis_path missing for {line_key}: {en_path}")
                else:
                    sections = parse_thesis(en_path)
                    for section in sections:
                        ex = build_example(
                            section=section,
                            line_key=line_key,
                            line_cfg=line_cfg,
                            lang="en",
                            thesis_filename=en_path.name,
                        )
                        f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        per_line_counts[line_key]["en"] += 1
                        written_total += 1

            if thesis_ja:
                ja_path = Path(thesis_ja)
                if not ja_path.exists():
                    print(f"WARN: thesis_path_ja missing for {line_key}: {ja_path}")
                else:
                    sections = parse_thesis(ja_path)
                    for section in sections:
                        ex = build_example(
                            section=section,
                            line_key=line_key,
                            line_cfg=line_cfg,
                            lang="ja",
                            thesis_filename=ja_path.name,
                        )
                        f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        per_line_counts[line_key]["ja"] += 1
                        written_total += 1

    print("Per-line counts (thesis sections):")
    for line_key, counts in per_line_counts.items():
        total = counts["en"] + counts["ja"]
        print(
            f"  {line_key:25s} en={counts['en']:3d}  ja={counts['ja']:3d}  total={total:3d}"
        )

    if skipped_lines:
        print(
            f"Skipped lines (thesis_path null in YAML — no thesis document): "
            f"{', '.join(skipped_lines)}"
        )

    print(f"examples written: {written_total} -> {args.out}")


if __name__ == "__main__":
    main()
