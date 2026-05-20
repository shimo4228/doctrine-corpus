"""Extract ADRs from all four research lines into doctrine-corpus JSONL.

For each ADR, emits up to two examples:

1. `shape: "judgment"` — Q = line-specific framing prefix + ADR Context,
                         A = ADR Decision (+ Consequences when present).
                         Skipped when Context or Decision is missing.
2. `shape: "explain"` — Q = line-specific explain prompt referencing the ADR
                        number + title, A = ADR full body verbatim.

Both shapes carry `meta.{line, source, lang, shape}` plus optional
`meta.status` / `meta.superseded_by` extracted from `## Status` when an ADR
records a non-accepted state. Deprecated ADRs (superseded / withdrawn) are
**included** rather than skipped — see the project plan and CLAUDE.md for the
rationale (thought-evolution as structured signal, not noise).

Configuration lives in `scripts/line_templates.yaml`. The script iterates the
four research lines (akc / contemplative-agent / aap / authorship-strategy)
in both EN and JA passes when the line has `has_ja: true`.

Provenance: rewritten from
`base-model-lab/experiments/disposition-lora/scripts/extract_adrs.py`. The
baseline handled only AKC + AAP (English only), assumed a fixed H2 order, and
treated Status as a no-op string. This rewrite parameterises by line, parses
H2 sections by heading text rather than position, and structures the
deprecation signal into metadata.

Usage:
    python scripts/extract_adrs.py
    python scripts/extract_adrs.py --lines akc authorship-strategy
    python scripts/extract_adrs.py --templates scripts/line_templates.yaml \\
        --out data/adrs.jsonl
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
DEFAULT_OUT = REPO_ROOT / "data" / "adrs.jsonl"

H1_RE = re.compile(r"^# ADR-(\d+):\s*(.+?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
ADR_REF_RE = re.compile(r"ADR-(\d+)")
BARE_NUM_RE = re.compile(r"\b(\d{3,4})\b")

# A handful of contemplative-moltbook .ja.md files use Japanese H2 headings
# rather than the English originals. Normalise to the English keys the parser
# expects downstream.
HEADING_ALIASES: dict[str, str] = {
    "ステータス": "status",
    "日付": "date",
    "コンテキスト": "context",
    "決定": "decision",
    "検討した代替案": "alternatives considered",
    "結果": "consequences",
    "帰結": "consequences",
}


@dataclass(frozen=True)
class ADR:
    line: str
    path: Path
    number: str
    title: str
    sections: dict[str, str]
    full_body: str
    status: str | None
    superseded_by: str | None
    lang: str

    @property
    def filename(self) -> str:
        return self.path.name


def parse_sections(text: str) -> dict[str, str]:
    """Split a markdown body into sections keyed by lowercased H2 heading.

    Heading text is normalised to lowercase so the caller can look up
    `Status`, `Context`, `Decision`, `Consequences`, etc. without worrying
    about case variation across lines.
    """
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return {}
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        raw_name = m.group(1).strip()
        name = HEADING_ALIASES.get(raw_name, raw_name.lower())
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()
    return sections


def classify_status(status_text: str) -> tuple[str | None, str | None]:
    """Return (status, superseded_by) from a Status section's raw text.

    Heuristic:
    - "withdrawn" anywhere → status: "withdrawn"
    - "superseded" anywhere → status: "superseded", extract first ADR-NNNN or
      bare 4-digit number after the superseded keyword
    - "accepted" anywhere → status: "accepted" (further metadata like
      "supersedes ADR-NNNN" is dropped — that's the *predecessor*'s job to
      record on its own Status line)
    - "proposed" anywhere → status: "proposed"
    - otherwise → (None, None)
    """
    if not status_text:
        return None, None

    text = status_text.strip()
    lower = text.lower()

    if "withdrawn" in lower:
        return "withdrawn", None

    if "superseded" in lower:
        # Try ADR-NNNN reference first, then bare digit run after the keyword.
        m = ADR_REF_RE.search(text)
        if m:
            return "superseded", f"ADR-{m.group(1).zfill(4)}"
        # Find a number that appears *after* the superseded keyword.
        idx = lower.find("superseded")
        tail = text[idx:]
        bm = BARE_NUM_RE.search(tail)
        if bm:
            return "superseded", f"ADR-{bm.group(1).zfill(4)}"
        return "superseded", None

    if lower.startswith("accepted") or " accepted" in lower:
        return "accepted", None

    if "proposed" in lower or "draft" in lower:
        return "proposed", None

    return None, None


def parse_adr(path: Path, line: str, lang: str) -> ADR | None:
    text = path.read_text(encoding="utf-8")
    title_m = H1_RE.search(text)
    if not title_m:
        return None
    number, title = title_m.group(1), title_m.group(2).strip()
    body_start = title_m.end()
    full_body = text[body_start:].strip()
    sections = parse_sections(text)
    status_text = sections.get("status", "")
    status, superseded_by = classify_status(status_text)
    return ADR(
        line=line,
        path=path,
        number=number,
        title=title,
        sections=sections,
        full_body=full_body,
        status=status,
        superseded_by=superseded_by,
        lang=lang,
    )


def collect_adrs(adr_dir: Path, line: str, has_ja: bool) -> list[ADR]:
    adrs: list[ADR] = []
    en_files = sorted(
        p
        for p in adr_dir.glob("*.md")
        if not p.name.endswith(".ja.md") and not p.name.startswith("README")
    )
    for path in en_files:
        adr = parse_adr(path, line=line, lang="en")
        if adr is not None:
            adrs.append(adr)

    if has_ja:
        ja_files = sorted(
            p for p in adr_dir.glob("*.ja.md") if not p.name.startswith("README")
        )
        for path in ja_files:
            adr = parse_adr(path, line=line, lang="ja")
            if adr is not None:
                adrs.append(adr)

    return adrs


def build_meta(
    adr: ADR, shape: str, source_fragment: str | None = None
) -> dict[str, Any]:
    source = f"docs/adr/{adr.filename}"
    if source_fragment:
        source = f"{source}#{source_fragment}"
    meta: dict[str, Any] = {
        "line": adr.line,
        "source": source,
        "lang": adr.lang,
        "shape": shape,
    }
    if adr.status is not None:
        meta["status"] = adr.status
    if adr.superseded_by is not None:
        meta["superseded_by"] = adr.superseded_by
    return meta


def judgment_example(adr: ADR, line_cfg: dict[str, Any]) -> dict | None:
    context = adr.sections.get("context")
    decision = adr.sections.get("decision")
    if not context or not decision:
        return None
    prefix = line_cfg["judgment_prefix"][adr.lang].strip()
    instruction = f"{prefix}\n\n{context}"
    completion = f"## Decision\n\n{decision}"
    consequences = adr.sections.get("consequences")
    if consequences:
        completion += f"\n\n## Consequences\n\n{consequences}"
    return {
        "messages": [
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": completion},
        ],
        "meta": build_meta(adr, shape="judgment", source_fragment="decision"),
    }


def explain_example(adr: ADR, line_cfg: dict[str, Any]) -> dict:
    prompt_template = line_cfg["explain_prompt"][adr.lang]
    instruction = prompt_template.format(number=adr.number, title=adr.title)
    return {
        "messages": [
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": adr.full_body},
        ],
        "meta": build_meta(adr, shape="explain"),
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

    written_judgment = 0
    written_explain = 0
    skipped_no_h1 = 0
    skipped_no_decision = 0
    per_line_counts: dict[str, dict[str, int]] = {}
    status_counts: dict[str, int] = {"accepted": 0, "superseded": 0, "withdrawn": 0, "proposed": 0, "unknown": 0}

    with args.out.open("w", encoding="utf-8") as f:
        for line_key, line_cfg in selected_lines.items():
            adr_dir = Path(line_cfg["adr_dir"])
            has_ja = bool(line_cfg.get("has_ja", False))

            if not adr_dir.exists():
                print(f"WARN: adr_dir missing for {line_key}: {adr_dir}")
                continue

            # Count skips per directory by re-globbing for H1-less files.
            for p in adr_dir.glob("*.md"):
                if p.name.startswith("README"):
                    continue
                if not has_ja and p.name.endswith(".ja.md"):
                    continue
                text = p.read_text(encoding="utf-8")
                if H1_RE.search(text) is None:
                    skipped_no_h1 += 1

            adrs = collect_adrs(adr_dir, line=line_key, has_ja=has_ja)
            per_line_counts[line_key] = {"judgment": 0, "explain": 0, "total_adrs": len(adrs)}

            for adr in adrs:
                status_key = adr.status if adr.status else "unknown"
                status_counts[status_key] = status_counts.get(status_key, 0) + 1

                je = judgment_example(adr, line_cfg)
                if je is None:
                    skipped_no_decision += 1
                else:
                    f.write(json.dumps(je, ensure_ascii=False) + "\n")
                    written_judgment += 1
                    per_line_counts[line_key]["judgment"] += 1

                ee = explain_example(adr, line_cfg)
                f.write(json.dumps(ee, ensure_ascii=False) + "\n")
                written_explain += 1
                per_line_counts[line_key]["explain"] += 1

    print("Per-line counts (ADRs / judgment pairs / explain pairs):")
    for line_key, counts in per_line_counts.items():
        print(
            f"  {line_key:25s} ADRs={counts['total_adrs']:3d}  "
            f"judgment={counts['judgment']:3d}  explain={counts['explain']:3d}"
        )

    print("Status distribution across all processed ADRs:")
    for status, count in status_counts.items():
        if count > 0:
            print(f"  {status:12s} {count:3d}")

    print("Skip counts:")
    print(f"  no H1 (skipped at glob stage):    {skipped_no_h1}")
    print(f"  no Context or Decision (judgment only): {skipped_no_decision}")

    total_written = written_judgment + written_explain
    print(
        f"examples written: {total_written} "
        f"(judgment={written_judgment}, explain={written_explain}) -> {args.out}"
    )


if __name__ == "__main__":
    main()
