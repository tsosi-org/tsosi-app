"""
Deployment script
TODO: Instantiate the SSH tunnel only once and re-use it for all commands. 
"""

import argparse
import os
import subprocess
import time
from pathlib import Path

import paramiko
from scp import SCPClient
from termcolor import colored

from .servers import SERVERS, ServerConfig, get_server

TSOSI_REPO_DIR = Path(__file__).resolve().parent.parent.parent
RELEASES_MAX_NB = 3


def create_ssh_client(server: ServerConfig):
    """
    Create and return a SSH client used to execute command on the given server
    over SSH.
    """
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_client.load_system_host_keys()
    ssh_client.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))

    ssh_client.connect(server.address, username=server.user, look_for_keys=True)
    return ssh_client


def scp_execute(server: ServerConfig, local_path: str, remote_path: str):
    """Perform a scp command."""
    ssh_client = create_ssh_client(server)
    print(
        f"{colored("RUNNING: ", "blue")} {colored(f"scp {local_path} {remote_path}", "yellow")}"
    )
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put(local_path, remote_path, recursive=True, preserve_times=False)

    ssh_client.close()


def ssh_execute(server: ServerConfig, command: str, count: int = 0):
    """
    Exectue SSH command on the target server and print channel's stdout
    and stderr to the current stdout.
    """
    ssh_client = create_ssh_client(server)
    stdin, stdout, stderr = ssh_client.exec_command(command)

    pre_cmd_txt = "RUNNING:"
    if count != 0:
        pre_cmd_txt = f"{count} - {pre_cmd_txt}"
    print(f"{colored(pre_cmd_txt, "blue")} {colored(command, "yellow")}")

    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print(err)
    if out:
        print(out)

    elif not out and not err:
        print("")

    ssh_client.close()

    exit_status = stdout.channel.recv_exit_status()
    if exit_status > 0:
        print(
            colored(
                f"Error while performing ssh command - Exit status: {exit_status}",
                "red",
            )
        )
        exit(exit_status)


def deploy(
    server_name: str,
    branch: str = None,
    skip_front_build=False,
    restart_celery=False,
):
    """
    Deploy the desired server with current code.
    """
    server = get_server(server_name)
    deploy_branch = branch if branch else server.default_branch
    config = {
        "server": server.name,
        "address": server.address,
        "user": server.user,
        "branch": deploy_branch,
        "skip_front_build": skip_front_build,
    }
    print(
        colored(
            f"Deploying TSOSI application with config:\n\n\t{"\n\t".join([f'{k}: {v}' for k, v in config.items()])}\n",
            "blue",
        )
    )
    resp = input(colored("Do you want to proceed ? [Y/n]", "yellow"))
    if resp not in ["Y", "y"]:
        print(colored(f"Aborted by input {resp}", "red"))
        return
    print("")

    # Build frontend deps
    frontend_dir = TSOSI_REPO_DIR / "frontend"
    if not skip_front_build:
        os.chdir(frontend_dir)

        cmds = ["npm install", "npm run build"]
        for cmd in cmds:
            print(f"{colored("RUNNING: ", "blue")} {colored(cmd, "yellow")}")
            result = subprocess.run(
                cmd.split(" "), capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                if result.stderr:
                    print(colored(result.stderr, "red"))
                print(result.stdout)
                exit(result.returncode)
            print(result.stdout)

    # Pull back-end code on server
    release_time = int(time.time() * 1000)

    remote_project_path = "/var/www"
    release_parent_dir = f"{remote_project_path}/releases"
    ssh_execute(server, f"mkdir -p {release_parent_dir}")

    release_dir = f"{release_parent_dir}/{release_time}"

    ssh_execute(server, f"mkdir -p {release_dir}")

    # Clone repo & extract only backend code
    ssh_execute(
        server,
        f"cd {release_dir} "
        f"&& git clone --branch {deploy_branch} https://github.com/tsosi-org/tsosi-app.git",
    )

    django_folder = "backend"
    ssh_execute(
        server,
        f"cd {release_dir} "
        "&& cp -r tsosi-app/backend . "
        "&& rm -r tsosi-app/ ",
    )

    # Install poetry & python deps.
    ssh_execute(
        server, "curl -sSL https://install.python-poetry.org | python3 -"
    )
    poetry_bin = "$HOME/.local/bin/poetry"
    ssh_execute(
        server,
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} config virtualenvs.in-project true",
    )

    ssh_execute(
        server,
        f"cd {release_dir}/{django_folder}/"
        f"&& {poetry_bin} install --without dev",
    )

    # Django tasks
    ssh_execute(
        server,
        f"ln -s $HOME/config/settings_local.py {release_dir}/{django_folder}/backend_site/settings_local.py",
    )

    ssh_execute(
        server,
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py collectstatic",
    )

    ssh_execute(
        server,
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py migrate",
    )
    # Custom tasks to execute after each deployment
    ssh_execute(
        server,
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py update_partners",
    )

    # Copy front files in release folder
    ssh_execute(server, f"mkdir -p {release_dir}/public")
    scp_execute(server, frontend_dir / "dist", f"{release_dir}/public")
    ssh_execute(
        server, f"cd {release_dir}/public && mv dist/* . && rm -r dist/"
    )

    # Update main symlink to the deployed version
    ssh_execute(
        server,
        "[ -L /var/www/current ] && unlink /var/www/current || echo '`current` symlink does not exist'",
    )
    ssh_execute(
        server,
        f"ln -s {release_dir} /var/www/current",
    )
    # Keep only N releases on the server
    ssh_execute(
        server,
        f"""
        dir_count=$(ls -d {release_parent_dir}/*/ | wc -l)
        if [ "$dir_count" -gt {RELEASES_MAX_NB} ]; then
            ls -d {release_parent_dir}/*/ | sort -n | head -n -3 | xargs rm -r
        else
            echo 'Less than {RELEASES_MAX_NB} found. No directories to delete.'
        fi
        """,
    )

    # Restart services
    ssh_execute(server, "sudo systemctl restart tsosi_gunicorn")
    ssh_execute(server, "sudo systemctl reload nginx")
    if restart_celery:
        ssh_execute(server, "sudo systemctl restart tsosi_celery")
        ssh_execute(server, "sudo systemctl restart tsosi_celery_beat")
    else:
        print("Skipped celery services restart.")

    print(colored("Deployment successful", "green"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "server_name",
        help=f"The name of the server to deploy, among: {",".join(SERVERS.keys())}",
    )
    parser.add_argument(
        "--branch",
        nargs="?",
        help="The branch used to pull the code. Default to `main`",
    )
    parser.add_argument(
        "--skip-front-build",
        help="If passed, do not build fresh front-end files in frontend/dist.",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--restart-celery",
        help="If passed, restart tsosi_celery and tsosi_celery_beat services.",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    args = parser.parse_args()
    deploy(
        args.server_name,
        args.branch,
        args.skip_front_build,
        args.restart_celery,
    )
