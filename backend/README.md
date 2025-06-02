

Welcome to the TSOSI back-end application, written in Python Django.

Follow the below procedure if you want to setup the application locally.

## Install python & deps

* Install python 3.12

* Install pipx & poetry for deps management. Poetry is a python dependency & environment manager. It should prefix any call to CLI programm installed in the project. 
    ```bash
    sudo apt install pipx
    pipx ensurepath
    pipx install poetry
    poetry --version
    ```

* Install python dependencies:
    ```bash
    # make poetry create virtualenvs in a .venv folder inside the project folder
    poetry config virtualenvs.in-project true
    poetry install
    ```

* Create a `settings_local.py` file for env. dependent Django settings:
    ```bash
    cd backend_site
    cp settings_local.example.py settings_local.py
    ```

## Database setup
* Install postgresql, and create user and tsosi database with the postgresql client:
    ```bash
    sudo apt install postgresql
    sudo su - postgres
    createuser -P tsosi_user
    createdb tsosi -O tsosi_user
    ```
* Create a `settings_local.py` file by copying the `settings_local.example.py` and replace database information with your database and user information.

* Run the database migrations to get the up-to-date database version.
    ```bash
    poetry run python manage.py migrate
    ```

## Install redis

* Install Redis manually or run [scripts/install_redis.sh](/scripts/install_redis.sh).
* Replace Redis connection parameters in your settings_local.py file. The default values should work (connecting with redis://127.0.0.1:6379/0) if you just installed Redis. 

## Celery

You may want to run a celery worker if you want to execute the data-related background tasks (data fetching & data processing).
You can do so by running a unique worker with unique concurrency by executing the following command.

```bash
poetry run celery -A backend_site worker --concurrency=1 --loglevel=INFO
```

**WARNING**: Increasing the workers or the concurrency might lead to errors as the tasks are not properly set up to handle concurrent data updates.

## Run the app with minimal data

You can load example data located in [tsosi/data/fixtures/prepared_files](./tsosi/data/fixtures/prepared_files/) by running the management command `ingest_test`:

```bash
poetry run python manage.py ingest_test
```

Then the Django dev server can be run with the command:

```bash
poetry run python manage.py runserver
```

You should then be able to navigate to the API at [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)

## Tests

Tests should be automatically discovered and run within VSCode when the Python extension is installed.

Alternatively, they can be run using the pytest command:
```bash
poetry run pytest
```

## postgreSQL commands

Basic commands to use in the psql shell:

* list all databases `\list`

* use "databaseName" database `\c databaseName`

* list all tables `\dt`

* list unique table information `\d+ tableName`

* list the size of each database
```sql
SELECT datname as db_name, pg_size_pretty(pg_database_size(datname)) as db_usage FROM pg_database;
```


## TSOSI App

All the code is placed in the TSOSI application, cf [README.md](tsosi/README.md).


## Test docker image

A basic docker image is used to run the tests on GitHub actions.
Perform the following steps to update image on the Github container registry (used by the workflow).


- You need a github token to be able to update the packages (including images) cf [GitHub docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry)

- Login against ghcr.io as mentioned in the doc:

```bash
export GITHUB_REGISTRY_TOKEN=<YOUR_TOKEN>
echo $GITHUB_REGISTRY_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

- Build the updated image, tag it accordingly and push it to the registry:

```bash
cd backend
docker build -t backend-test-env -f test.Dockerfile .
docker images # Copy the build image's ID
docker tag <IMAGE_ID> ghcr.io/tsosi-org/backend-test-env:latest
docker push ghcr.io/tsosi-org/backend-test-env:latestt
```


