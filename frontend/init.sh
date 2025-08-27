#!/bin/bash
# Script to be run after the repository is pulled for the first time
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

cd $SCRIPT_DIR

# Install javascript dependencies
echo -e "\nInstalling Javascript dependencies"
npm ci

# Create dev .env file
if ! [ -f ".env.development" ]; then
    echo -e "\nNo define env file. Using default dev one"
    cp ".env.development.example" ".env.development"
fi
