
IMAGE_NAME="spotlight"
CONTAINER_ID=$(docker ps -a -q --filter "ancestor=$IMAGE_NAME" | head -n 1)
 
DIR_NAME="./outputs"
docker cp $CONTAINER_ID:/home/results $DIR_NAME