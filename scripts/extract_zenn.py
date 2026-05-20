"""Extract Zenn articles into doctrine-corpus JSONL.

Reads `--articles-dir/*.md`, parses Zenn-CLI frontmatter, chunks long articles
on H2/H3 boundaries, emits a JSONL file where each line carries
`meta.{line, source, lang, shape}` so downstream filtering / ablation can
isolate Zenn output from ADR output.

Provenance: ported from
`base-model-lab/experiments/disposition-lora/scripts/extract_zenn.py`
with CLI defaults pointing at this repo's `data/` directory and `meta` added
to every example. Instruction templates intentionally remain in
chunk-as-completion form (`shape: "explain"`) — judgment-shape Q&A from Zenn
material is the Stage C `extract_judgment_qa.py` responsibility.

Usage:
    python scripts/extract_zenn.py
    python scripts/extract_zenn.py --articles-dir ~/MyAI_Lab/zenn-content/articles \\
        --out data/zenn.jsonl --min-lines 50 --chunk-threshold 300
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

ZENN_ARTICLES_DIR = Path.home() / "MyAI_Lab" / "zenn-content" / "articles"
DEFAULT_OUT = Path(__file__).parent.parent / "data" / "zenn.jsonl"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
TITLE_RE = re.compile(r'^title:\s*"?(.*?)"?\s*$', re.MULTILINE)
PUBLISHED_RE = re.compile(r"^published:\s*(\w+)\s*$", re.MULTILINE)
H2_H3_RE = re.compile(r"^(##{1,2} )", re.MULTILINE)


@dataclass(frozen=True)
class Article:
    path: Path
    title: str
    body: str
    published: bool

    @property
    def line_count(self) -> int:
        return self.body.count("\n") + 1

    @property
    def slug(self) -> str:
        return self.path.stem


def parse_article(path: Path) -> Article | None:
    """Parse a Zenn article. Returns None if the file is not a valid article."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    frontmatter, body = m.group(1), m.group(2).strip()

    title_m = TITLE_RE.search(frontmatter)
    if not title_m:
        return None
    title = title_m.group(1).strip()

    pub_m = PUBLISHED_RE.search(frontmatter)
    published = pub_m is not None and pub_m.group(1).lower() == "true"

    return Article(path=path, title=title, body=body, published=published)


def chunk_body(body: str, threshold: int) -> list[str]:
    """Chunk on H2/H3 boundaries when body exceeds threshold lines.

    Each chunk preserves its leading heading. Short bodies return as a single chunk.
    """
    if body.count("\n") + 1 <= threshold:
        return [body]

    parts: list[str] = []
    indices = [m.start() for m in H2_H3_RE.finditer(body)]
    if not indices:
        return [body]

    if indices[0] > 0:
        parts.append(body[: indices[0]].rstrip())
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(body)
        chunk = body[start:end].strip()
        if chunk:
            parts.append(chunk)

    parts = [p for p in parts if p.count("\n") + 1 >= 10]
    return parts


def to_example(article: Article, chunk: str, chunk_idx: int, total_chunks: int) -> dict:
    if total_chunks == 1:
        instruction = f"「{article.title}」というタイトルで Zenn 記事を書いて。"
    else:
        instruction = (
            f"「{article.title}」という Zenn 記事の中で、以下のセクションを書いて "
            f"(全 {total_chunks} セクション中の {chunk_idx + 1} 番目)。"
        )
    return {
        "messages": [
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": chunk},
        ],
        "meta": {
            "line": "zenn",
            "source": f"articles/{article.slug}.md",
            "lang": "ja",
            "shape": "explain",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles-dir", type=Path, default=ZENN_ARTICLES_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-lines", type=int, default=50)
    ap.add_argument("--chunk-threshold", type=int, default=300)
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    md_files = sorted(p for p in args.articles_dir.glob("*.md"))

    written = 0
    skipped_unpublished = 0
    skipped_short = 0
    skipped_unparsable = 0

    with args.out.open("w", encoding="utf-8") as f:
        for path in md_files:
            art = parse_article(path)
            if art is None:
                skipped_unparsable += 1
                continue
            if not art.published:
                skipped_unpublished += 1
                continue
            if art.line_count < args.min_lines:
                skipped_short += 1
                continue

            chunks = chunk_body(art.body, args.chunk_threshold)
            for idx, chunk in enumerate(chunks):
                example = to_example(art, chunk, idx, len(chunks))
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
                written += 1

    print(f"input articles: {len(md_files)}")
    print(f"  unparsable:   {skipped_unparsable}")
    print(f"  unpublished:  {skipped_unpublished}")
    print(f"  too short:    {skipped_short}")
    print(f"examples written: {written} -> {args.out}")


if __name__ == "__main__":
    main()
