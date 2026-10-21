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

# Enable the versioned git hooks (.githooks/), unless hooks are already
# configured for this repository. The pre-commit hook regenerates the models'
# ER diagram (see tsosi/models/README.md)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && ! git config --local --get core.hooksPath >/dev/null; then
    echo -e "\nEnabling the git hooks of .githooks/"
    git config --local core.hooksPath .githooks \
        || echo "Could not set core.hooksPath, run: git config core.hooksPath .githooks"
fi

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
