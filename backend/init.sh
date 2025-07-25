#!/bin/bash
# Script to be run after the repository is pulled for the first time
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

cd $SCRIPT_DIR

# This need to be re-run once the container is connected to
# bc poetry config is user-dependent. The one from the docker is not read here.
poetry config virtualenvs.in-project true

# Install python deps
echo -e "\nInstalling Python dependencies"
poetry install --no-root

# Create settings_local.py file
if ! [ -f "backend_site/settings_local.py" ]; then
    echo -e "\nNo define settings_local.py file. Using default dev one"
    cp "backend_site/settings_local.dev.py" "backend_site/settings_local.py"
fi

# Create default log & media directories
mkdir -p _no_git/logs
mkdir -p _no_git/media

# Migrate database
echo -e "\nMigrating database"
poetry run python manage.py migrate

# Fill static data
echo -e "\nUpdating static data"
poetry run python manage.py fill_static_data