
Welcome to the TSOSI back-end application, written in Python Django.

This describes how to setup and run the various backend services: Django web server, Celery worker, Redis, PostgreSQL, run tests.

See [here](./tsosi/README.md) to jump to TSOSI Django app, containing all our code. 

See [here](./deployment/README.md) to know more on our deployment process.

# Manual setup

**ONLY WHEN NOT USING THE DEVCONTAINER**

## Install python & deps

* Install python 3.12. The app has not been tested for other Python versions.

* Install pipx & poetry for deps management. Poetry is a python dependency & environment manager. It should prefix any call to python CLI program installed in the project. 
    ```bash
    sudo apt install pipx
    pipx ensurepath
    pipx install poetry
    poetry --version
    # make poetry create virtualenvs in a .venv folder inside the project folder
    poetry config virtualenvs.in-project true
    ```

* Install python dependencies:
    ```bash
    # You need to execute this in backend/ directory where pyproject.toml is located
    poetry install --no-root
    ```

* Create a `settings_local.py` file for env. dependent Django settings:
    ```bash
    cd backend_site
    cp settings_local.dev.py settings_local.py
    ```

## Database setup
* Install postgresql, and create user and tsosi database with the postgresql client:
    ```bash
    sudo apt install postgresql
    sudo su - postgres
    createuser -P tsosi_user
    createdb tsosi -O tsosi_user
    ```
* Update your `settings_local.py` file with the database name, user and password information (in the `DATABASES` setting).

* Run the database migrations to get the up-to-date database version.
    ```bash
    poetry run python manage.py migrate
    ```

## Install redis

* Install Redis manually or run our [redis installer script](/scripts/install_redis.sh)
    ```bash
    sudo ../scripts/install_redis.sh
    ```
    
* Replace Redis connection parameters in your `settings_local.py` file. The default values should work (connecting with redis://127.0.0.1:6379/0) if you just installed Redis. 


# Run the app

## Poetry

Poetry is used to manage the python dependencies of the project and related commands.
See [poetry doc](https://python-poetry.org/).

## Editor setup (VSCode)

The repo ships no `.vscode/settings.json`. All tooling is configured through
standard files:

- Formatting/imports: `[tool.black]` and `[tool.isort]` in
  [pyproject.toml](./pyproject.toml) (line length 80). Run them with
  `poetry run black .` and `poetry run isort .`, or let the
  `ms-python.black-formatter` / `ms-python.isort` extensions pick the config up
  automatically.
- Indentation / newlines: [.editorconfig](../.editorconfig) at the repo root.
- Test config: `[tool.pytest.ini_options]` in `pyproject.toml`.

One manual step per machine: point VSCode at the Poetry virtualenv with
**Command Palette → "Python: Select Interpreter" → `./backend/.venv/bin/python`**
(this choice is stored in VSCode's workspace state, not in the repo). To enable
format-on-save and the Test Explorer, add to your **user** settings:

```jsonc
"[python]": { "editor.formatOnSave": true },
"python.testing.pytestEnabled": true,
"python.testing.cwd": "${workspaceFolder}/backend"
```

## Django

You can run the Django dev server by running:

```bash
poetry run python manage.py runserver
```

You should then be able to navigate to the API at [http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)

## Celery

We use [celery](https://docs.celeryq.dev/en/stable/) to run automated background tasks.

You may want to run a celery worker if you want to execute the data-related background tasks (data fetching & data processing).
You can do so by running a unique worker with unique concurrency by executing the following command.

```bash
poetry run celery -A backend_site worker --concurrency=1 --loglevel=INFO
```

**WARNING**: Increasing the workers or the concurrency might lead to errors as the tasks are not properly set up to handle concurrent data updates.

## Run the app with minimal data

The management command `ingest_test` loads example data from the `tsosi/data/fixtures/prepared_files/` folder:

```bash
poetry run python manage.py ingest_test
```

**WARNING**: this folder is currently not versioned in the repository, so the command ingests nothing out of the box.


## Tests

Run the test suite from the `backend/` directory:
```bash
poetry run pytest
```

They are also discovered by the VSCode Test Explorer once `python.testing.pytestEnabled`
is set in your user settings (see [Editor setup](#editor-setup-vscode)).


## TSOSI App

All the code is placed in the TSOSI application, cf [README.md](./tsosi/README.md) for a thorough description of our data workflow.


## Test docker image

A basic docker image is used to run the tests on GitHub actions.
Perform the following steps to update image on the Github container registry (used by the workflow).

Ideally, the image should be updated whenever a python dependency is added or modified.


- You need a github token to be able to update the packages (including images) cf [GitHub docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry)

- Login against ghcr.io as mentioned in the doc:

```bash
export GITHUB_REGISTRY_TOKEN=<YOUR_TOKEN>
echo $GITHUB_REGISTRY_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

- Build the updated image, tag it accordingly and push it to the registry:

```bash
cd backend
docker build -t tsosi-app-backend-test-env -f test.Dockerfile .
docker images # Copy the build image's ID
docker tag <IMAGE_ID> ghcr.io/tsosi-org/tsosi-app-backend-test-env:latest
docker push ghcr.io/tsosi-org/tsosi-app-backend-test-env:latest
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

