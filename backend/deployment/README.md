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
    sudo ln -s /etc/nginx/sites-available/tsosi-app /etc/nginx/sites-enabled/
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

* Create a `tsosi_celery_beat` service to run the Celery Beat scheduler (periodic tasks, see `TSOSI_CELERY_BEAT_SCHEDULE`). Copy the file [tsosi_celery_beat.service](./tsosi_celery_beat.service) in `/etc/systemd/system/` and enable the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable tsosi_celery_beat.service
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

* Prepare log rotation, cf. **Log rotation** section below.


## Deployment

You can deploy any server by running the deploy script:
```bash
cd backend/
poetry run python -m deployment.deploy <SERVER_NAME>
```
Options:
* `--branch` - The branch used to pull the code from (only for back-end, front-end is built locally). Defaults to the server's `default_branch` in [servers.py](./servers.py). The local checked-out branch must match it.
* `--skip-front-build` - If passed, the script will deploy already built front-end files in `frontend/dist` instead of building new ones. Useful when deploying several times in a row without changes on the frontend. The script refuses if they were built for another server (`frontend_mode` in `frontend/dist/deployment.json`).
* `--celery-no-restart` - If passed, the script will not restart the `tsosi_celery` and `tsosi_celery_beat` services on the server. Not recommended.

The front-end is built with the server's `frontend_mode` ([servers.py](./servers.py)), i.e. the Vite mode reading `frontend/.env.{mode}`: `production` for prod, `dev-server` for dev.

The deploy script clones the branch from GitHub: push it first.

## Dev server

`dev` in [servers.py](./servers.py): https://dev.tsosi.org, to test a branch on a copy of the production data before deploying it to prod. The server is `tsosi-dev.u-ga.fr` (129.88.205.79, Debian 13): log in as `debian` (sudo) to administer it, the deploy script logs in as `deployer`.

```bash
git push -u origin <BRANCH>
cd backend/
poetry run python -m deployment.deploy dev --branch <BRANCH>
```

Its default branch is `dev`.

### Differences with prod

It is prepared as in **Server preparation** above, with these differences:

* Packages: Debian 13 comes with Python 3.13, which the backend supports (`>=3.12`). The Poetry installer needs `venv`:
    ```bash
    sudo apt install git curl python3-venv python3-dev nginx postgresql redis-server rsync
    ```
    Redis comes from Debian's packages (8.0), not [install_redis.sh](/scripts/install_redis.sh). `nginx` and `logrotate` are in `/usr/sbin`, outside `debian`'s `PATH`.
* SSL certificate: the Hub's session and CSRF cookies are only sent over HTTPS (`DEBUG = False`). The Let's Encrypt certificate comes from [acme.sh](https://github.com/acmesh-official/acme.sh), installed for `root` (`/root/.acme.sh/`), with a DNS challenge through the OVH API of the `tsosi.org` zone (its API keys are saved in `/root/.acme.sh/account.conf`), not certbot. Its root cron renews the certificate, copies it to `/etc/ssl/` and reloads nginx:
    ```bash
    # As root
    acme.sh --issue --server letsencrypt --dns dns_ovh -d dev.tsosi.org
    acme.sh --install-cert -d dev.tsosi.org --ecc \
        --key-file /etc/ssl/private/dev.tsosi.org.key \
        --fullchain-file /etc/ssl/certs/dev.tsosi.org.fullchain.pem \
        --reloadcmd "systemctl reload nginx"
    ```
    Then replace the default nginx site with the dev config [tsosi-app-dev.nginx.config](./tsosi-app-dev.nginx.config):
    ```bash
    sudo cp tsosi-app-dev.nginx.config /etc/nginx/sites-available/tsosi-app
    sudo ln -s /etc/nginx/sites-available/tsosi-app /etc/nginx/sites-enabled/
    sudo rm /etc/nginx/sites-enabled/default
    sudo /usr/sbin/nginx -t && sudo systemctl reload nginx
    ```
    The dev config sends `X-Robots-Tag: noindex` and a `robots.txt` disallowing everything, as the site is a copy of production.
* `settings_local.py`: start from [settings_local.prod.py](/backend/backend_site/settings_local.prod.py), with its own `SECRET_KEY` and database password (`HOST = "localhost"`), and:
    ```python
    ALLOWED_HOSTS = ["dev.tsosi.org", "127.0.0.1"]
    # Used in the Hub's login e-mails and the sitemap.
    TSOSI_FRONTEND_URL = "https://dev.tsosi.org"
    # Login e-mails are printed in the gunicorn log
    # (`sudo journalctl -u tsosi_gunicorn`). Use the e-mail settings of prod
    # instead to receive them (the servers can't reach SMTP ports).
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    # In the log folder of `deployer`, rotated by logrotate.
    TSOSI_MAIN_LOG_FILE = "/var/log/tsosi/tsosi_app.log"
    TSOSI_DATA_LOG_FILE = "/var/log/tsosi/tsosi_data.log"
    TSOSI_DJANGO_LOG_FILE = "/var/log/tsosi/django.log"
    ERROR_LOG_FILE = "/var/log/tsosi/error.log"
    ```
    Leave `TSOSI_LINKEDIN` out: the LinkedIn authorization is prod's.
* Data: restore a production dump before the first deploy, so that its `migrate` also tests the migrations on the production data. From your machine, with the latest dump of [pull_prod_db.sh](/scripts/pull_prod_db.sh) (`backend/_no_git/db_dumps/prod_*.dump`):
    ```bash
    scp backend/_no_git/db_dumps/<PROD_DUMP> tsosi-dev:/tmp/tsosi.dump
    # On the dev server, in the empty `tsosi` database
    sudo -u postgres pg_restore --no-owner --no-privileges --role=tsosi_user -d tsosi --exit-on-error /tmp/tsosi.dump
    ```
    Then the logos, through a local copy:
    ```bash
    rsync -a deployer@tsosi.u-ga.fr:/tsosi_media/ backend/_no_git/tsosi_media/
    rsync -a backend/_no_git/tsosi_media/ deployer@tsosi-dev.u-ga.fr:/tsosi_media/
    ```
* Celery Beat runs the same schedule as prod (enrichment, data updates from external sources).

## SSL certificates

We use certbot to automatically get certificates from letsencrypt.
Just follow the tutorial on certbot page: https://certbot.eff.org/instructions?ws=nginx&os=snap.

Certificate data is stored in `/etc/letsencrypt/live/{{ server_name }}/`

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