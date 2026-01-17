#!/bin/bash

# =========================
# Configuration
# =========================
CONTAINER_NAME="relaxed_bhaskara"
BASE_DIR="./outputs"
PREFIX="results"
NUM_RUNS=2

mkdir -p "$BASE_DIR"

# =========================
# Find container
# =========================
CONTAINER_ID=$(docker ps -a -q --filter "name=^/${CONTAINER_NAME}$")

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: container '$CONTAINER_NAME' not found."
    exit 1
fi

# Start container if needed
docker start "$CONTAINER_ID" > /dev/null
echo "Using container $CONTAINER_ID"

# =========================
# Runs
# =========================
for ((run=0; run<NUM_RUNS; run++)); do
    echo "=== Run $run ==="

    # Find next results_N
    i=0
    while [ -d "$BASE_DIR/${PREFIX}_$i" ]; do
        ((i++))
    done

    HOST_TARGET_DIR="$BASE_DIR/${PREFIX}_$i"
    mkdir -p "$HOST_TARGET_DIR"

    echo "Results will be copied to $HOST_TARGET_DIR"

    # -------------------------
    # Run experiments INSIDE container
    # -------------------------
    docker exec -i "$CONTAINER_ID" bash -c "
        cd /home

        source /opt/conda/etc/profile.d/conda.sh
        conda activate spotlight-ae

        ./run-ae.sh single --model RESNET --target EDP --technique Spotlight --scale Edge
    "

    # -------------------------
    # Copy results OUT
    # -------------------------
    docker cp "$CONTAINER_ID:/home/results" "$HOST_TARGET_DIR"

    echo "Run $run finished."
done

echo "All runs completed."
