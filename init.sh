#!/bin/bash
# Script to be run after the repository is pulled for the first time
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

cd $SCRIPT_DIR

echo -e "\nInitializing tsosi-app repository"

echo -e "\nbackend/ Initialization..."
bash backend/init.sh

echo -e "\nfrontend/ Initialization..."
bash frontend/init.sh