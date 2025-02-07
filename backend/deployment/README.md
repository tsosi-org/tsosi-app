# Deployment process

You can use the deploy.py script to deploy a specific server.
It expects the target server to have been prepared with by following the **Server preparation** section below.

The preparation process is basically to install and enable all services used by the application:
* Nginx - web server
* Gunicorn - WSGI http server
* PostgreSQL - Relational database
* Redis - In-memory datastore
* Celery - Python automated task queue & scheduler


## Server preparation

* Linux with Python 3.12 installed

* `deployer` user created for deployment process. This user will execute all necessary commands on the server to run the Tsosi app, such as updating files and starting services. You must enable SSH login with your SSH key. The user will need access to the /var/www folder for deployment along with sudo rights for a few service commands. You can add the following permissions by running `sudo visudo`:
    ```
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart nginx, /usr/bin/systemctl start nginx, /usr/bin/systemctl stop nginx, /usr/bin/systemctl status nginx 
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_gunicorn, /usr/bin/systemctl start tsosi_gunicorn, /usr/bin/systemctl stop tsosi_gunicorn, /usr/bin/systemctl status tsosi_gunicorn
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart redis-server, /usr/bin/systemctl start redis-server, /usr/bin/systemctl stop redis-server, /usr/bin/systemctl status redis-server
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_celery, /usr/bin/systemctl start tsosi_celery, /usr/bin/systemctl stop tsosi_celery, /usr/bin/systemctl status tsosi_celery
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_celery_beat, /usr/bin/systemctl start tsosi_celery_beat, /usr/bin/systemctl stop tsosi_celery_beat, /usr/bin/systemctl status tsosi_celery_beat
    ```

* Poetry package manager installed:
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

* Create socket & service for gunicorn (WSGI HTTP server to serve our Django application). If you're using our common setup, just copy the files [tsosi_gunicorn.service](./tsosi_gunicorn.service) and [tsosi_gunicorn.socket](./tsosi_gunicorn.socket) in `/etc/systemd/system/`.
    Then start the socket:
    ```bash
    sudo systemctl enable tsosi_gunicorn.socket
    ```
    A `tsosi_gunicorn` service is created and should be started automatically when there's traffic on the socket.  

* Install Nginx web server and add a config for the tsosi application.
    ```bash
    sudo apt install nginx
    # Create server configuration - See example below
    sudo nano /etc/nginx/sites-available/tsosi-app
    # Enable configuration
    sudo ln -s /etc/nginx/sites-available/myproject /etc/nginx/sites-enabled/
    # Check nginx for syntax errors:
    sudo nginx -t
    # Restart service
    sudo systemctl restart nginx    
    ```

    Example configuration can be found at [tsosi-app.nginx.config](./tsosi-app.nginx.config).
    

* Install redis datastore, cf [install_redis.sh](/scripts/install_redis.sh)

* Create a `tsosi_celery` service to run celery worker(s). If you're using our common setup, just copy the file [tsosi_celery.service](./tsosi_celery.service) in `/etc/systemd/system/` and enable the service:
    ```bash
    sudo systemctl enable tsosi_celery.service
    ```

* Folder or dedicated storage volume for storing images.

* Running PostgreSQL service and database.
    ```bash
    sudo apt install postgresql
    sudo su - postgres
    createuser -P tsosi_user
    createdb tsosi -O tsosi_user
    ```

* Prepared `settings_local.py` with specific environment settings for the Django application.

* Prepare a media repository to store fetched logos. Ex:
    ```bash
    cd /
    sudo mkdir tsosi_media
    sudo chown deployer:www-data tsosi_media
    sudo chmod 755 tsosi_media
    ``` 

* Prepare a folder for logs with rights for the user running the Django app and the Celery services, example:
    ```bash
    mkdir /var/log/tsosi
    sudo chown -R deployer:deployer /var/log/tsosi
    ```



## Deployment

You can deploy any server by running the deploy script:
```bash
cd backend/
poetry run python -m deployment.deploy <SERVER_NAME>
```
Options:
* `--branch` - The branch used to pull the code from (only for back-end, front-end is built locally).
* `--skip-front-build` - Whether to use already built front-end files in `frontend/dist` or to build new ones.