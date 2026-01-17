CONTAINER_NAME="strange_tharp"  # spotlight_container
CONTAINER_ID=$(docker ps -a -q --filter "name=$CONTAINER_NAME" | head -n 1)

# Start the container if it’s stopped
docker start "$CONTAINER_ID"

# Exec into it
docker exec -it "$CONTAINER_ID" /bin/bash
