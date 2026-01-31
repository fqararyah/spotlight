#!/bin/bash

# =========================
# Configuration
# =========================
CONTAINER_NAME="relaxed_bhaskara"
BASE_DIR="./outputs"
PREFIX="results"
NUM_RUNS=8

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

MODELS=(
  CONV00
  CONV01
  CONV02
  MatMul03
  CONV04
  CONV05
  CONV06
  MatMul07
  CONV08
  MatMul09
  CONV10
  CONV11
  CONV12
  CONV13
  CONV14
  CONV15
  CONV16
  CONV17
  CONV18
  CONV19
  CONV20
  CONV21
  MatMul22
  CONV23
  CONV24
  CONV25
  CONV26
  CONV27
  CONV28
  MatMul29
  CONV30
  CONV31
  MatMul32
  CONV33
  CONV34
  CONV35
  CONV36
  CONV37
  CONV38
  CONV39
  CONV40
  CONV41
  MatMul42
  CONV43
  CONV44
  CONV45
  CONV46
  CONV47
  CONV48
  CONV49
  CONV50
  CONV51
  CONV52
  CONV53
  CONV54
  CONV55
  MatMul56
  CONV57
  CONV58
  CONV59
  MatMul60
  CONV61
  CONV62
  CONV63
  CONV64
  CONV65
  CONV66
  CONV67
)

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
    for MODEL in "${MODELS[@]}"; do
    echo "------------------------------------------------------"
    echo "Running model: $MODEL"
    echo "------------------------------------------------------"

    docker exec -i "$CONTAINER_ID" bash -c "
        cd /home
        source /opt/conda/etc/profile.d/conda.sh
        conda activate spotlight-ae
        ./run-ae.sh single --model $MODEL --target EDP --technique Spotlight --scale Edge
    "
    done

    # -------------------------
    # Copy results OUT
    # -------------------------
    docker cp "$CONTAINER_ID:/home/results" "$HOST_TARGET_DIR"

    echo "Run $run finished."
done

echo "All runs completed."
