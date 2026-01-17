IMAGE_NAME="spotlight"
CONTAINER_ID=$(docker ps -a -q --filter "ancestor=$IMAGE_NAME" | head -n 1)

BASE_DIR="./outputs"
PREFIX="results"

# Ensure base directory exists
mkdir -p "$BASE_DIR"

# Find next available results_N directory
i=0
while [ -d "$BASE_DIR/${PREFIX}_$i" ]; do
  ((i++))
done

TARGET_DIR="$BASE_DIR/${PREFIX}_$i"

# Copy results from container
docker cp "$CONTAINER_ID:/home/results" "$TARGET_DIR"
