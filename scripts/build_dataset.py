"""Merge zenn.jsonl + adrs.jsonl, shuffle, and split 90/10 into train/valid.

mlx-lm `lora` expects training data at `<data-dir>/train.jsonl` and
validation data at `<data-dir>/valid.jsonl`. This script produces both.

Usage:
    python build_dataset.py
    python build_dataset.py --seed 42 --val-fraction 0.1
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--val-fraction", type=float, default=0.1)
    args = ap.parse_args()

    zenn = read_jsonl(args.data_dir / "zenn.jsonl")
    adrs = read_jsonl(args.data_dir / "adrs.jsonl")
    combined = zenn + adrs

    rng = random.Random(args.seed)
    rng.shuffle(combined)

    val_n = max(1, int(len(combined) * args.val_fraction))
    valid = combined[:val_n]
    train = combined[val_n:]

    write_jsonl(args.data_dir / "train.jsonl", train)
    write_jsonl(args.data_dir / "valid.jsonl", valid)

    print(f"sources: zenn={len(zenn)}, adrs={len(adrs)}, total={len(combined)}")
    print(f"  train: {len(train)} -> {args.data_dir / 'train.jsonl'}")
    print(f"  valid: {len(valid)} -> {args.data_dir / 'valid.jsonl'}")


if __name__ == "__main__":
    main()
