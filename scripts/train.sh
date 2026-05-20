#!/usr/bin/env bash
# Train a verification LoRA adapter on the assembled doctrine-corpus using
# mlx-lm. The adapter is NOT a publish target — it is a disposable test
# runner used to detect whether Phase 0's "mannerism wrapper" failure
# mode (voice transferred, content hallucinated) recurs after the Stage
# A-C corpus rework. See docs/adr/0005-*.md for the Stage D verdict and
# base-model-lab/experiments/disposition-lora/findings.md for the Phase
# 0 precedent.
#
# Usage:
#   bash scripts/train.sh                         # full run (~75-95 min on 16GB Mac)
#   DRY_RUN=1 bash scripts/train.sh               # 2-iter smoke test (architecture compat check)
#   MODEL=mlx-community/Qwen3-8B-4bit bash scripts/train.sh  # explicit override

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

cd "$(dirname "$0")/.."

# Qwen3.5-9B/4B/2B all OOM on 16GB Mac during first train iter — mlx-lm
# does not handle the Qwen3.5 hybrid arch (Gated DeltaNet + MoE) backward
# pass within budget. Stage D pins Qwen3-8B-4bit to match Phase 0 and keep
# direct comparability with disposition-lora/findings.md.
MODEL="${MODEL:-mlx-community/Qwen3-8B-4bit}"
DATA_DIR="${DATA_DIR:-./corpus/v0.1.0}"
ADAPTER_PATH="${ADAPTER_PATH:-./outputs/adapters/v0}"
ITERS="${ITERS:-400}"
NUM_LAYERS="${NUM_LAYERS:-16}"
BATCH_SIZE="${BATCH_SIZE:-1}"
LEARNING_RATE="${LEARNING_RATE:-1e-5}"
STEPS_PER_EVAL="${STEPS_PER_EVAL:-50}"
VAL_BATCHES="${VAL_BATCHES:-2}"
MAX_SEQ_LENGTH="${MAX_SEQ_LENGTH:-1024}"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  ITERS=2
  STEPS_PER_EVAL=2
  ADAPTER_PATH="./outputs/adapters/dry_run"
  echo "[dry-run] iters=$ITERS, adapter=$ADAPTER_PATH"
fi

mkdir -p "$ADAPTER_PATH"

echo "model           : $MODEL"
echo "data            : $DATA_DIR"
echo "adapter         : $ADAPTER_PATH"
echo "iters           : $ITERS"
echo "num-layers      : $NUM_LAYERS"
echo "batch-size      : $BATCH_SIZE"
echo "lr              : $LEARNING_RATE"
echo "max-seq-length  : $MAX_SEQ_LENGTH"
echo "grad-checkpoint : on"
echo

uv run python -m mlx_lm lora \
  --model "$MODEL" \
  --train \
  --data "$DATA_DIR" \
  --iters "$ITERS" \
  --batch-size "$BATCH_SIZE" \
  --num-layers "$NUM_LAYERS" \
  --learning-rate "$LEARNING_RATE" \
  --adapter-path "$ADAPTER_PATH" \
  --val-batches "$VAL_BATCHES" \
  --steps-per-eval "$STEPS_PER_EVAL" \
  --max-seq-length "$MAX_SEQ_LENGTH" \
  --grad-checkpoint
