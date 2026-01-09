
IMAGE_NAME="spotlight"
CONTAINER_ID=$(docker ps -a -q --filter "ancestor=$IMAGE_NAME" | head -n 1)

docker cp $CONTAINER_ID:/Results/* ./outputs