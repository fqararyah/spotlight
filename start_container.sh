IMAGE_NAME="spotlight"
CONTAINER_ID=$(docker ps -a -q --filter "ancestor=$IMAGE_NAME" | head -n 1)

# Start the container if it’s stopped
docker start "$CONTAINER_ID"

# Exec into it
docker exec -it "$CONTAINER_ID" /bin/bash
