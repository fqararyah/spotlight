#!/bin/bash

# Container and image names
IMAGE_NAME="spotlight"
CONTAINER_NAME=$(docker ps --filter "ancestor=$IMAGE_NAME" --format "{{.Names}}")

# Container working directory
APP_PATH=/home

# Paths
HOST_REPO=$(pwd)          # Assuming you run script from the root of spotlight repo
SRC_PY_DIR="$HOST_REPO/src"
HOST_SH_DIR="$HOST_REPO"

# Copy all Python files from src/
for py_file in "$SRC_PY_DIR"/*.py; do
    [ -e "$py_file" ] || continue  # skip if no files
    docker cp "$py_file" $CONTAINER_NAME:$APP_PATH/src/
done

# # Copy all shell scripts directly in spotlight root
# for sh_file in "$HOST_SH_DIR"/*.sh; do
#     [ -e "$sh_file" ] || continue
#     docker cp "$sh_file" $CONTAINER_NAME:$APP_PATH/
# done