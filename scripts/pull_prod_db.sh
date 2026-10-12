#!/bin/bash
# Replace the local database with a copy of the production one.
#
# The dump runs on the prod server through SSH (so its pg_dump matches the prod
# PostgreSQL version) and the restore runs inside the local docker `db` service.
# The prod database password is asked on the command line and sent through the
# SSH stdin, so it never shows in a command line or a file.
#
# Usage: scripts/pull_prod_db.sh [-y] [--media] [--restore FILE]
#   -y              don't ask for confirmation before overwriting the local database
#   --media         also rsync the prod media files into backend/_no_git/media/
#   --restore FILE  only restore FILE (e.g. a local backup) into the local database
#
# The defaults match the prod settings_local.py. Override them with env
# variables, or in a backend/_no_git/prod_db.env file defining them:
#   PROD_SSH          SSH destination of the prod server (default: tsosi, from ~/.ssh/config)
#   PROD_DB_USER      prod database user (default: tsosi_user)
#   PROD_DB_NAME      prod database name (default: tsosi)
#   PROD_DB_HOST      prod database host, seen from the server (default: localhost)
#   PROD_DB_PORT      prod database port (default: 5432)
#   PROD_PG_DUMP      pg_dump command on the server (default: pg_dump)
#   PROD_MEDIA_ROOT   prod MEDIA_ROOT, used with --media (default: /tsosi_media)
set -euo pipefail
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
NO_GIT_DIR="$ROOT_DIR/backend/_no_git"

ASSUME_YES=false
SYNC_MEDIA=false
RESTORE_FILE=""
while [ $# -gt 0 ]; do
    case "$1" in
        -y) ASSUME_YES=true ;;
        --media) SYNC_MEDIA=true ;;
        --restore)
            RESTORE_FILE="${2:?--restore needs a dump file}"
            [ -f "$RESTORE_FILE" ] || { echo "No such file: $RESTORE_FILE" >&2; exit 1; }
            shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
    shift
done

if [ -f "$NO_GIT_DIR/prod_db.env" ]; then
    source "$NO_GIT_DIR/prod_db.env"
fi
PROD_SSH="${PROD_SSH:-tsosi}"
PROD_DB_USER="${PROD_DB_USER:-tsosi_user}"
PROD_DB_NAME="${PROD_DB_NAME:-tsosi}"
PROD_DB_HOST="${PROD_DB_HOST:-localhost}"
PROD_DB_PORT="${PROD_DB_PORT:-5432}"
PROD_PG_DUMP="${PROD_PG_DUMP:-pg_dump}"
PROD_MEDIA_ROOT="${PROD_MEDIA_ROOT:-/tsosi_media}"

# Same compose project as dev.sh, to use the DevContainer database volume.
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$ROOT_DIR")_devcontainer}"
COMPOSE=(docker compose -p "$COMPOSE_PROJECT_NAME" -f "$ROOT_DIR/.devcontainer/docker-compose.yml")
LOCAL_DB_USER="${LOCAL_DB_USER:-tsosi_user}"
LOCAL_DB_NAME="${LOCAL_DB_NAME:-tsosi_db}"

start_local_db() {
    echo "Starting the local database ..."
    "${COMPOSE[@]}" up -d db
    until "${COMPOSE[@]}" exec -T db pg_isready -q; do sleep 1; done
}

confirm_overwrite() {
    $ASSUME_YES && return
    echo "The local database $LOCAL_DB_NAME will be replaced by $1."
    echo "Stop the local celery worker first."
    read -rp "Continue? [y/N] " answer
    [[ "$answer" =~ ^[yY]$ ]] || { echo "Aborted."; exit 1; }
}

# Replace the whole public schema by the dump content, in a single transaction:
# on any error the local database is left untouched. Dropping the schema rather
# than using `pg_restore --clean` also removes the local tables that the dump
# doesn't have (e.g. from migrations not deployed yet), whose foreign keys would
# block the restore. COMMIT is only sent once the whole dump went through.
restore_dump() {
    # Check the archive is readable before touching the local database.
    "${COMPOSE[@]}" exec -T db pg_restore -l < "$1" > /dev/null
    echo "Restoring $1 ..."
    {
        echo "SET client_min_messages = warning; BEGIN;"
        echo "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        "${COMPOSE[@]}" exec -T db pg_restore --no-owner --no-privileges -f - < "$1" \
            && echo "COMMIT;"
    } | "${COMPOSE[@]}" exec -T db psql -q -v ON_ERROR_STOP=1 \
        -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" > /dev/null
}

if [ -n "$RESTORE_FILE" ]; then
    start_local_db
    confirm_overwrite "$RESTORE_FILE"
    restore_dump "$RESTORE_FILE"
    echo "Done."
    exit 0
fi

DUMP_DIR="$NO_GIT_DIR/db_dumps"
mkdir -p "$DUMP_DIR"
chmod 700 "$DUMP_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
PROD_DUMP="$DUMP_DIR/prod_$TIMESTAMP.dump"
LOCAL_BACKUP="$DUMP_DIR/local_before_restore_$TIMESTAMP.dump"

read -rsp "Password of $PROD_DB_USER on the prod database: " PROD_PASSWORD
echo

echo "Dumping $PROD_DB_NAME from $PROD_SSH ..."
# LC_ALL silences the locale warnings of the Ubuntu pg_dump wrapper.
REMOTE_CMD="export LC_ALL=C.UTF-8; IFS= read -r PGPASSWORD; export PGPASSWORD"
REMOTE_CMD+="; exec $PROD_PG_DUMP"
REMOTE_CMD+=" -Fc --no-owner --no-privileges"
REMOTE_CMD+=" -h $(printf %q "$PROD_DB_HOST") -p $(printf %q "$PROD_DB_PORT")"
REMOTE_CMD+=" -U $(printf %q "$PROD_DB_USER") $(printf %q "$PROD_DB_NAME")"
if ! printf '%s\n' "$PROD_PASSWORD" | ssh "$PROD_SSH" "$REMOTE_CMD" > "$PROD_DUMP"; then
    rm -f "$PROD_DUMP"
    echo "The prod dump failed." >&2
    exit 1
fi
unset PROD_PASSWORD
echo "Prod dump: $PROD_DUMP ($(du -h "$PROD_DUMP" | cut -f1))"

start_local_db

echo "Backing up the local database ..."
"${COMPOSE[@]}" exec -T db pg_dump -Fc -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME" > "$LOCAL_BACKUP"
echo "Local backup: $LOCAL_BACKUP"

confirm_overwrite "the prod one"
restore_dump "$PROD_DUMP"

if $SYNC_MEDIA; then
    echo "Syncing media files ..."
    mkdir -p "$NO_GIT_DIR/media"
    rsync -a --info=stats1 "$PROD_SSH:${PROD_MEDIA_ROOT%/}/" "$NO_GIT_DIR/media/"
fi

echo -e "\nDone. If your branch has migrations that prod doesn't have, run:"
echo "  cd backend && poetry run python manage.py migrate"
echo "To roll back:"
echo "  scripts/pull_prod_db.sh --restore $LOCAL_BACKUP"
