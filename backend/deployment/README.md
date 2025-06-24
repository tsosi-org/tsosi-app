# Deployment process

You can use the deploy.py script to deploy a specific server.
It expects the target server to have been prepared with by following the **Server preparation** section below.

The preparation process consists basically in installing and enabling all services used by the application and setting correct permission:

* Nginx - web server
* Gunicorn - WSGI http server
* PostgreSQL - Relational database
* Redis - In-memory datastore
* Celery - Python automated task queue & scheduler

### Note

All services are running using systemd with corresponding unit files.
The default places them in the `/etc/systemd/system/`. One could try to put them as user services in `/etc/systemd/user/` instead of system-wide services. Cf. [this doc](https://doc.ubuntu-fr.org/creer_un_service_avec_systemd) for example. 

## Server preparation

* Linux with Python 3.12 installed

* `deployer` user created for deployment process.


    This user will execute all necessary commands on the server to run the app, such as updating files and starting services. 
    
    * You must enable SSH login with your SSH key - copy your public key in
    `/home/deployer/.ssh/authorized_keys` or use `ssh-copy-id` command to do it for you.

    * The user will need access to the /var/www folder for deployment. Update the permission accordingly if required, ex:
        ```bash
        sudo chown deployer:www-data /var/www
        ```
        
    * `deployer` will need sudo rights for a few service commands. You can add the required permissions by running `sudo visudo` and pasting the following :

    ```
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart nginx, /usr/bin/systemctl start nginx, /usr/bin/systemctl stop nginx, /usr/bin/systemctl status nginx, /usr/bin/systemctl reload nginx
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_gunicorn, /usr/bin/systemctl start tsosi_gunicorn, /usr/bin/systemctl stop tsosi_gunicorn, /usr/bin/systemctl status tsosi_gunicorn
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart redis-server, /usr/bin/systemctl start redis-server, /usr/bin/systemctl stop redis-server, /usr/bin/systemctl status redis-server
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_celery, /usr/bin/systemctl start tsosi_celery, /usr/bin/systemctl stop tsosi_celery, /usr/bin/systemctl status tsosi_celery
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/systemctl restart tsosi_celery_beat, /usr/bin/systemctl start tsosi_celery_beat, /usr/bin/systemctl stop tsosi_celery_beat, /usr/bin/systemctl status tsosi_celery_beat
    deployer ALL=(ALL:ALL) NOPASSWD: /usr/bin/chown -R deployer\:deployer /var/www/releases/
    ```

* Prepare a folder for logs with rights for the user running the Django app and the Celery services, example:
    ```bash
    mkdir /var/log/tsosi
    sudo chown -R deployer:deployer /var/log/tsosi
    ```

* Create socket & service for gunicorn (WSGI HTTP server to serve our Django application). If you're using our common setup, just copy the files [tsosi_gunicorn.service](./tsosi_gunicorn.service) and [tsosi_gunicorn.socket](./tsosi_gunicorn.socket) in `/etc/systemd/system/`.
    Then start the socket:
    ```bash
    sudo systemctl daemon-reload # Reload unit files
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
    

* Install redis datastore, you can run the installer script [install_redis.sh](/scripts/install_redis.sh) on the server.

* Create a `tsosi_celery` service to run celery worker(s). If you're using our common setup, just copy the file [tsosi_celery.service](./tsosi_celery.service) in `/etc/systemd/system/` and enable the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable tsosi_celery.service
    ```

* Prepare a media repository to store fetched logos. It can be a local folder or a dedicated volume. Ex:
    ```bash
    cd /
    sudo mkdir tsosi_media
    sudo chown deployer:www-data tsosi_media
    sudo chmod 755 tsosi_media
    ``` 

* Running PostgreSQL service and database.
    ```bash
    sudo apt install postgresql
    sudo su - postgres
    createuser -P tsosi_user
    createdb tsosi -O tsosi_user
    ```

* Prepare the `settings_local.py` with specific environment settings for the Django application.
    
    You can copy-paste the [settings_local.prod.py](/backend/backend_site/settings_local.prod.py) and modify the secrets you set (database password, media folder, ...).
    The deploy script expects it to be located at `/home/deployer/config/settings_local.py`.

* Prepare log rotation, cd **Log rotation** section below.


## Deployment

You can deploy any server by running the deploy script:
```bash
cd backend/
poetry run python -m deployment.deploy <SERVER_NAME>
```
Options:
* `--branch` - The branch used to pull the code from (only for back-end, front-end is built locally).
* `--skip-front-build` - If passed, the script will deploy already built front-end files in `frontend/dist` instead of building new ones. Useful when deploying several times in a row without changes on the frontend.
* `--celery-no-restart` - If passed, the script will not restart celery services on the server. Not recommended.

## SSL certificates

We use certbot to automatically get certificates from letsencrypt.
Just follow the tutorial on certbot page: https://certbot.eff.org/instructions?ws=nginx&os=snap.

Certifiate data is stored in `/etc/letsencrypt/live/{{ server_name }}/`

## Log rotation

We use default `logrotate` program to rotate logs.

The utility is called everyday by default on ubuntu systems (can be found in `/etc/cron.daily/logrotate`) so that you just need to write the desired configuration. If the desired frequency is more than daily, you'll need to add your own crontab.

The prod configuration is the following one:

```
/var/log/tsosi/*.log {
    rotate 5 # Number of rotation before deletion
    weekly  # Frequency of rotation.
    minsize 5k # Log files smaller than this are ignored even if the date criteria is met.
    maxsize 100k # Rotate logs before the date-frequency if the file is bigger that maxsize
    missingok # No error if missing file
    notifempty # Don't rotate empty log file. Useful only for date-based rotation.
    copytruncate # Truncate the original log file in place instead of moving it then re-creating it.
    compress # Compress old log files
}
```
You can write this config in a new file named `tsosi` in `/etc/logrotate.d/` and voilà!

**Beware** that you need to remove the "comments" for the file to be correctly read by logrotate.

You can run the log rotate command to check the conf syntax with the following command (it will rotate the log if the criterias are met):

```bash
sudo logrotate /etc/logrotate.conf --debug
```