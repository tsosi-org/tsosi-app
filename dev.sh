#!/bin/bash
# Start the local dev stack on the host (see README): PostgreSQL & Redis in
# docker, then the Django dev server, the Vite dev server and the celery worker.
# Ctrl+C stops the 3 processes, the docker services keep running.
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

cd $SCRIPT_DIR

# Use the DevContainer compose project name so that both share the same
# database volume. Override it with the COMPOSE_PROJECT_NAME env variable.
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$SCRIPT_DIR")_devcontainer}"
COMPOSE=(docker compose -p "$COMPOSE_PROJECT_NAME" -f .devcontainer/docker-compose.yml)

echo -e "\nStarting PostgreSQL & Redis (compose project: $COMPOSE_PROJECT_NAME)"
"${COMPOSE[@]}" up -d db redis
until "${COMPOSE[@]}" exec -T db pg_isready -q; do sleep 1; done

# Stop every child process on exit, and exit as soon as one of them stops.
trap 'trap - EXIT INT TERM; kill 0 2>/dev/null' EXIT INT TERM
export PYTHONUNBUFFERED=1

run() {
    local name=$1 dir=$2
    shift 2
    (cd "$dir" && "$@" 2>&1 | sed -u "s/^/[$name] /") &
}

run api backend poetry run python manage.py runserver
run front frontend npm run dev
run celery backend poetry run celery -A backend_site worker --concurrency=1 --loglevel=INFO

wait -n
