# tsosi-app

This is the repository of the TSOSI web platform including both front-end and back-end of the web application (see [https://tsosi.org](https://tsosi.org)).

TSOSI aims to gather, store, expose and disseminate the financial transfers made to Open Science Infrastructures. For more information, see our [About page](https://tsosi.org/pages/about)

## Backend

See related [README.md](/backend/README.md) to run the Django app locally and our data workflow.

## Frontend

See related [README.md](/frontend/README.md) to run the Vue.js app locally.


## Local dev using containerized env

You can use the declared VSCode DevContainer to automatically setup a full-fledged
dev environment and use VSCode within it.


### Requirements

This requires docker to be installed on your machine and to install VSCode's DevContainer extension: [ms-vscode-remote.remote-containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

#### Install docker

Install docker using one of the following method:

- With our [docker-installer script](/scripts/install_docker.sh) (bundled from docker docs)
    ```bash
    sudo bash scripts/install_docker.sh
    # You may need to reboot your machine so that VSCode has access to the docker engine.
    ```
- **OR** Manual installation, see [docker docs](https://docs.docker.com/engine/install/ubuntu/).

#### Install DevContainer extension

Install VSCode DevContainer extension: VSCode's DevContainer extension: [ms-vscode-remote.remote-containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)


### Setup env & settings files

You need to create a `postgres.env` file that will store the Postgres database secrets used by the application.

The easiest is to copy the default one:

```bash
cp .devcontainer/postgres.example.env .devcontainer/postgres.env
```

**OPTIONNAL** If you change the default values, you will need to
manually create your Django settings file ([`settings_local.py`](./backend/backend_site/settings_local.py)) and edit the `DATABASE` setting with the secrets you used for your database:

```bash
cp backend/backend_site/settings_local.dev.py backend/backend_site/settings_local.py
# Edit the file
```

**TODO** Make our Django settings use env. variables for the database connection so that it can be stored in a share .env file for both the app and the database services. 


### Build and launch devcontainer

Open Command palette (`Ctrl + Maj + p`).

Launch the command **DevContainers: Reopen in container**.
This will trigger the build of the dev container and open vscode within it, then run our repository [init script](./init.sh).

You're now good to go!
You can run dev servers as following:

- Django (backend) dev server:
    ```bash
    cd backend
    poetry python manage.py runserver
    ```

- Vite (frontend) dev server:
    ```bash
    cd frontend
    npm run dev
    ```
Navigate to [http://localhost:5173](http://localhost:5173).

And also run the celery worker for more advance usage:
```bash
poetry run celery -A backend_site worker --concurrency=1 --loglevel=INFO
```

## Local dev with manual installation (NOT RECOMMENDED)

Follow the instructions in the dedicated [frontend]((./frontend/README.md)) and [backend](./backend/README.md) **README.md** files. 