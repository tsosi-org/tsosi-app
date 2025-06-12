# tsosi-app

This is the repository of the TSOSI web platform including both front-end and back-end of the application.


## Local dev with manual installation

### Backend

See related [README.md](/backend/README.md) to install and run the Django app locally.

### Frontend

See related [README.md](/frontend/README.md) to install and run the Vue.js app locally.

## Local dev using containerized env

You can use the declared VSCode DevContainer to automatically setup a full-fledged
dev environment and use VSCode within it.


### Requirements

This requires docker to be installed on your machine and to install VSCode's DevContainer extension: [ms-vscode-remote.remote-containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

#### Install docker

Install docker using one of the following method:

1. With our docker-installer script (taken from docker docs)
    ```bash
    sudo bash scripts/install_docker.sh
    ```
2. Manual installation, see docker docs. Something like:
    ```bash
    sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```


#### Install DevContainer extension


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