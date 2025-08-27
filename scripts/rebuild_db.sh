#!/bin/bash
# This was used when all services were directly installed on the host machine.
# This should be rewritten with the containers setup.
set -e
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Drop Postgres DB
# Restart the service to drop existing connections.
sudo systemctl restart postgresql

sudo -u postgres bash -c 'dropdb tsosi; createdb tsosi -O tsosi_user;' &
pid=$!
wait $pid
exit_status=$?

if [ $exit_status -ne 0 ];then
    echo "DB dropping and creation as postgres user crashed"
    exit $exit_status
fi
 
# Make migration files
cd $SCRIPT_DIR
cd ../backend/tsosi/migrations
FILE_PATTERN="0*_*.py"
if ls $FILE_PATTERN 1> /dev/null 2>&1; then
    rm $FILE_PATTERN
fi
cd ../..
poetry run python manage.py makemigrations tsosi
poetry run python manage.py migrate
