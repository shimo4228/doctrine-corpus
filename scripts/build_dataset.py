"""Merge N source JSONL files, shuffle, and split 90/10 into train/valid.

mlx-lm `lora` expects training data at `<data-dir>/train.jsonl` and
validation data at `<data-dir>/valid.jsonl`. This script produces both.

Without `--source` arguments the legacy 2-source behaviour is preserved:
`data-dir/zenn.jsonl` + `data-dir/adrs.jsonl`. With one or more `--source`
arguments, only those files are merged.

Usage:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --source data/zenn.jsonl --source data/adrs.jsonl
    python scripts/build_dataset.py --source data/adrs.jsonl --seed 42 --val-fraction 0.1
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_SOURCES = ("zenn.jsonl", "adrs.jsonl")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def resolve_sources(args: argparse.Namespace) -> list[Path]:
    if args.source:
        return [Path(p) for p in args.source]
    return [args.data_dir / name for name in DEFAULT_SOURCES]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument(
        "--source",
        action="append",
        default=None,
        help=(
            "Path to a source JSONL file. Repeatable. "
            "When omitted, falls back to {data-dir}/zenn.jsonl + adrs.jsonl."
        ),
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--val-fraction", type=float, default=0.1)
    args = ap.parse_args()

    args.data_dir.mkdir(parents=True, exist_ok=True)
    sources = resolve_sources(args)

    combined: list[dict] = []
    per_source_counts: list[tuple[Path, int]] = []
    for source in sources:
        examples = read_jsonl(source)
        per_source_counts.append((source, len(examples)))
        combined.extend(examples)

    if not combined:
        print("WARN: no examples loaded from any source")
        for source, count in per_source_counts:
            print(f"  {source}: {count}")
        return

    rng = random.Random(args.seed)
    rng.shuffle(combined)

    val_n = max(1, int(len(combined) * args.val_fraction))
    valid = combined[:val_n]
    train = combined[val_n:]

    write_jsonl(args.data_dir / "train.jsonl", train)
    write_jsonl(args.data_dir / "valid.jsonl", valid)

    print("Per-source counts:")
    for source, count in per_source_counts:
        print(f"  {source}: {count}")
    print(f"total examples: {len(combined)}")
    print(f"  train: {len(train)} -> {args.data_dir / 'train.jsonl'}")
    print(f"  valid: {len(valid)} -> {args.data_dir / 'valid.jsonl'}")


if __name__ == "__main__":
    main()
