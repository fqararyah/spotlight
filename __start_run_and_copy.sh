#!/bin/bash
set -e

IMAGE_NAME="spotlight"
BASE_DIR="./outputs"
PREFIX="results"
NUM_RUNS=5

mkdir -p "$BASE_DIR"

# Get container (assumes exactly one)
CONTAINER_ID=$(docker ps -a -q --filter "ancestor=$IMAGE_NAME" | head -n 1)

# Start container if needed
docker start "$CONTAINER_ID" >/dev/null

for ((run=0; run<NUM_RUNS; run++)); do
  echo "=== Run $run ==="

  # Find next results directory
  i=0
  while [ -d "$BASE_DIR/${PREFIX}_$i" ]; do
    ((i++))
  done
  TARGET_DIR="$BASE_DIR/${PREFIX}_$i"

  # Run experiments (BLOCKING)
  docker exec "$CONTAINER_ID" bash -lc "/path/run-experiments.sh"

  # Copy results
  docker cp "$CONTAINER_ID:/home/results" "$TARGET_DIR"

  echo "Results copied to $TARGET_DIR"
done
