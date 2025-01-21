

Welcome to the TSOSI back-end application, written in Python Django.

Follow the below procedure if you want to setup the application locally.

## Install python & deps

* Install python 3.12

* Install pipx & poetry for deps management
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
    cd site
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
    python manage.py migrate
    ```

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