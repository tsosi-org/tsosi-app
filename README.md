# tsosi-app

This is the repository of the TSOSI web platform including both front-end and back-end of the application.


## Stuff

Install docker

```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```


## Dev container

Develop using the provided dev container.

Once built and connected to the container, you will need to mark the repository as safe for git if it's mounted from the local one:
```bash
git config --global --add safe.directory /workspaces/tsosi-app
```

## Connecting to local database from the container

You need to configure several things if you're running the app's container with default network mode `bridge`.
You should be able to access the database correctly if you're running the network mode `host`.

### Figure out your machine and container IP addresses on docker interface 
You need to figure out what's your machine IP address on the interface (usually 172.17.0.1), which usually corresponds to the bridge's gateway IP address.

```bash
docker network inspect bridge
```

Find the gateway IP adress in the correct bridge along with the container's IP.

### Edit PostgreSQL config to listen to connection on that interface

You need to make the Postgres server listen for incoming connections on that interface.
By default, the server only listens to requests to localhost (127.0.0.1) IP and only allows requests from localhost.
Navigate to the postgres config folder to edit the correct files:
```bash
cd /etc/postgresql/{postgres_version}/main
```

Edit the `postgresql.conf` file to add the found IP address to the listening addresses (ex: `listening_addresses='localhost,172.17.0.1'`).

Edit the `pg_hba.conf` file to add either the docker subnet or only this container to perform queries to the Postgres server.

```
# Authorize connections for all local docker containers
host	all		all		172.17.0.0/16		md5

# Only authorize the container with IP 172.17.0.2
host	all		all		172.17.0.2/32		md5
```

Restart postgresql service
```bash
sudo systemctl restart postgresql
```

Warning: for the config to work, the docker daemon and maybe even the docker container must be running so that postgres can listen to the correct network.
You can just restart the service if it's not working.


### Run dev servers

You can't run the dev server at the classic 127.0.0.1 IP address if connections are expected from outside the docker container:

* You can allow all connections by using the wildcard IP address 0.0.0.0
    ```bash
    python manage.py runserver 0.0.0.0:8000
    ```
* You can allow only connections from the Host machine by using the container's IP address on the docker network interface (ex: 172.17.0.2).
    ```bash
    python manage.py runserver 172.17.0.2:8000
    ```