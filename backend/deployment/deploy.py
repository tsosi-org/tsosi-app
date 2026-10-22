"""
Deployment script.
For usage information, run:
```
poetry run python -m deployment.deploy --help
```
"""

import argparse
import datetime
import json
import os
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko
from termcolor import colored

from .servers import SERVERS, ServerConfig, get_server

TSOSI_REPO_DIR = Path(__file__).resolve().parent.parent.parent
RELEASES_MAX_NB = 3
UPLOAD_TIMEOUT_SECONDS = 300
SSH_KEEPALIVE_SECONDS = 30


def create_ssh_client(server: ServerConfig):
    """
    Create and return a SSH client used to execute command on the given server
    over SSH.

    :param server:  The target server config.
    """
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_client.load_system_host_keys()
    ssh_client.load_host_keys(Path.home() / ".ssh/known_hosts")

    ssh_client.connect(server.address, username=server.user, look_for_keys=True)
    ssh_client.get_transport().set_keepalive(SSH_KEEPALIVE_SECONDS)
    return ssh_client


def upload_dir(
    local_dir: str,
    remote_dir: str,
    server: ServerConfig,
    ssh_client: paramiko.SSHClient,
):
    """
    Upload the content of `local_dir` into `remote_dir` (which must exist)
    as a single tar.gz archive, then extract it on the server.
    """
    print(
        f"{colored("RUNNING: ", "blue")} {colored(f"upload {local_dir}/* -> {remote_dir}", "yellow")}"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = Path(tmp_dir) / "upload.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(local_dir, arcname=".")
        subprocess.run(
            [
                "scp",
                "-q",
                "-o",
                "ServerAliveInterval=30",
                str(archive_path),
                f"{server.user}@{server.address}:{remote_dir}/upload.tar.gz",
            ],
            check=True,
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )
    ssh_execute(
        f"cd {remote_dir} && tar -xzf upload.tar.gz && rm upload.tar.gz",
        ssh_client=ssh_client,
    )


def ssh_execute(
    command: str,
    server: ServerConfig | None = None,
    ssh_client: paramiko.SSHClient | None = None,
    count: int = 0,
):
    """
    Exectue SSH command on the target server and print channel's stdout
    and stderr to the current stdout.
    You can either:
        -   pass a `ServerConfig` object. A SSH connection will be opened only
            for this command execution and closed afterwards.
        -   pass a `SSHClient` object. The command will be executed using this
            client.
    """
    close_client = ssh_client is None
    if ssh_client is None:
        if server is None:
            raise Exception("Either `server` or `ssh_client` is required.")
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
        print()

    if close_client:
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


def format_dict_string(d: dict, indent="\t") -> str:
    """
    Format an indented string from a dict, to be displayed in the terminal.
    """
    line_sep = f"\n{indent}"
    return f"{indent}{line_sep.join([f'{k}: {v}' for k, v in d.items()])}"


def run_local_cmd(cmd: str, print_stdout=True) -> str:
    """
    Run the given command with the current user in a subprocess.
    The current program/script will exit if the command fails.
    """
    print(f"{colored("RUNNING: ", "blue")} {colored(cmd, "yellow")}")
    result = subprocess.run(
        cmd.split(" "), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        if result.stderr:
            print(colored(result.stderr, "red"))
        print(result.stdout)
        exit(result.returncode)
    if print_stdout:
        print(result.stdout)
    return result.stdout


def deploy(
    server_name: str,
    branch: str | None = None,
    skip_front_build=False,
    celery_no_restart=False,
):
    """
    Deploy latest commit code to the desired server.

    :param server_name:         The name of the server to deploy. Ex: `prod`.
                                The name is the key of the `SERVERS` mapping,
                                cf. servers.py.
    :param branch:              The branch name to deploy. Default to the
                                server's `default_branch`.
    :param skip_front_build:    Whether to skip the build of fresh frontend
                                files. If `True`, it will copy existing files
                                in frontend/dist.
    :param celery_no_restart:   Whether to not restart Celery systemd services
                                on the server. Default to `False`.
    """
    server = get_server(server_name)
    deploy_branch = branch if branch else server.default_branch
    config = {
        "server": server.name,
        "address": server.address,
        "user": server.user,
        "branch": deploy_branch,
        "frontend_mode": server.frontend_mode,
        "skip_front_build": skip_front_build,
        "restart_celery": not celery_no_restart,
    }
    print(
        colored(
            f"Deploying TSOSI application with config:\n\n"
            f"{format_dict_string(config)}\n",
            "blue",
        )
    )
    resp = input(colored("Do you want to proceed ? [Y/n]", "yellow"))
    if resp not in ["Y", "y"]:
        print(colored(f"Aborted by input {resp}", "red"))
        return
    print()

    # Check that the current branch is the same as the input one
    current_branch = run_local_cmd(
        "git branch --show-current", print_stdout=False
    ).strip()
    if current_branch != deploy_branch:
        print(
            colored(
                f"The current local branch `{current_branch}` "
                f"does not match the input one `{deploy_branch}`.\n"
                f"Please checkout the branch `{deploy_branch}`"
                f"\n\ngit checkout {deploy_branch}",
                "red",
            )
        )
        exit(1)
    # Get current commit info
    sep = ";~;"
    info = {"hash": "%H", "author": "%ae", "commit_date": "%cI", "title": "%s"}
    format_string = sep.join(info.values())

    commit_info = run_local_cmd(
        f"git log -1 --pretty=format:{format_string}", print_stdout=False
    ).strip()
    deployment_info_object = {
        label: value
        for label, value in zip(info.keys(), commit_info.split(sep))
    }
    # Get current HEAD / Commit
    print(
        colored(
            "\nDeploying current commit:\n\n"
            f"{format_dict_string(deployment_info_object)}"
            "\n",
            "blue",
        )
    )

    # Build frontend deps
    frontend_dir = TSOSI_REPO_DIR / "frontend"
    deployment_file = frontend_dir / "dist/deployment.json"
    if not skip_front_build:
        os.chdir(frontend_dir)

        # `npm run build` in 2 steps: it doesn't pass the mode on to vite.
        cmds = [
            "npm ci",
            "npm run type-check",
            f"npm run build-only -- --mode {server.frontend_mode}",
        ]
        for cmd in cmds:
            run_local_cmd(cmd)
    else:
        # The existing build must target this server's API, e.g. not deploy
        # a production build on the dev server.
        built_mode = None
        if deployment_file.exists():
            with open(deployment_file) as f:
                # Deployments before the dev server only built for prod.
                built_mode = json.load(f).get("frontend_mode", "production")
        if built_mode != server.frontend_mode:
            print(
                colored(
                    f"The frontend files in frontend/dist were built in mode "
                    f"`{built_mode}`, not `{server.frontend_mode}`.\n"
                    "Deploy without --skip-front-build.",
                    "red",
                )
            )
            exit(1)

    # Add a deployment file with information on the deployed code
    deployment_info_object["date"] = datetime.datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    deployment_info_object["frontend_mode"] = server.frontend_mode

    with open(deployment_file, "w") as f:
        json.dump(deployment_info_object, f, indent=2)

    # Pull back-end code on server
    ssh_client = create_ssh_client(server)
    release_time = int(time.time() * 1000)

    remote_project_path = "/var/www"
    release_parent_dir = f"{remote_project_path}/releases"
    ssh_execute(f"mkdir -p {release_parent_dir}", ssh_client=ssh_client)

    release_dir = f"{release_parent_dir}/{release_time}"

    ssh_execute(f"mkdir -p {release_dir}", ssh_client=ssh_client)

    # Clone repo & extract only backend code
    ssh_execute(
        f"cd {release_dir} "
        f"&& git clone --branch {deploy_branch} https://github.com/tsosi-org/tsosi-app.git",
        ssh_client=ssh_client,
    )

    django_folder = "backend"
    ssh_execute(
        f"cd {release_dir} "
        "&& cp -r tsosi-app/backend . "
        "&& rm -r tsosi-app/ ",
        ssh_client=ssh_client,
    )

    # Install poetry & python deps.
    ssh_execute(
        "curl -sSL https://install.python-poetry.org | POETRY_VERSION=2.1.3 python3 -",
        ssh_client=ssh_client,
    )
    poetry_bin = "$HOME/.local/bin/poetry"
    ssh_execute(
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} config virtualenvs.in-project true",
        ssh_client=ssh_client,
    )

    ssh_execute(
        f"cd {release_dir}/{django_folder}/"
        f"&& {poetry_bin} install --without dev",
        ssh_client=ssh_client,
    )

    # Django tasks
    ssh_execute(
        f"ln -s $HOME/config/settings_local.py {release_dir}/{django_folder}/backend_site/settings_local.py",
        ssh_client=ssh_client,
    )

    ssh_execute(
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py collectstatic",
        ssh_client=ssh_client,
    )

    ssh_execute(
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py migrate",
        ssh_client=ssh_client,
    )
    # Custom tasks to execute after each deployment
    ssh_execute(
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py fill_static_data",
        ssh_client=ssh_client,
    )
    # Initial history records of the existing rows, for the models without
    # any history yet.
    ssh_execute(
        f"cd {release_dir}/{django_folder}/ "
        f"&& {poetry_bin} run python manage.py populate_history --auto",
        ssh_client=ssh_client,
    )

    # Copy front files in release folder
    ssh_execute(f"mkdir -p {release_dir}/public", ssh_client=ssh_client)
    upload_dir(
        f"{frontend_dir}/dist",
        f"{release_dir}/public",
        server=server,
        ssh_client=ssh_client,
    )

    # Fetch blog content and newsletters, then refreshed hourly by the
    # `refresh_news` task.
    ssh_execute(
        f"cd {release_dir}/backend && {poetry_bin} run python3 manage.py fetch_blog",
        ssh_client=ssh_client,
    )
    ssh_execute(
        f"cd {release_dir}/backend && {poetry_bin} run python3 manage.py refresh_newsletters",
        ssh_client=ssh_client,
    )

    # Update main symlink to the deployed version
    ssh_execute(
        "[ -L /var/www/current ] && unlink /var/www/current"
        " || echo '`current` symlink does not exist'",
        ssh_client=ssh_client,
    )
    ssh_execute(f"ln -s {release_dir} /var/www/current", ssh_client=ssh_client)

    # Restart services
    ssh_execute("sudo systemctl restart tsosi_gunicorn", ssh_client=ssh_client)
    ssh_execute("sudo systemctl reload nginx", ssh_client=ssh_client)
    if not celery_no_restart:
        ssh_execute(
            "sudo systemctl restart tsosi_celery", ssh_client=ssh_client
        )
        ssh_execute(
            "sudo systemctl restart tsosi_celery_beat", ssh_client=ssh_client
        )
    else:
        print("Skipped celery services restart.")

    # Keep only N releases on the server
    # Give ownership to deployer to be able to delete the releases.
    # Sometimes a *.pyc file gets created with root owner
    ssh_execute(
        "sudo chown -R deployer:deployer /var/www/releases/",
        ssh_client=ssh_client,
    )
    ssh_execute(
        f"""
        dir_count=$(ls -d {release_parent_dir}/*/ | wc -l)
        if [ "$dir_count" -gt {RELEASES_MAX_NB} ]; then
            ls -d {release_parent_dir}/*/ | sort -n | head -n -3 | xargs rm -r
        else
            echo 'Less than {RELEASES_MAX_NB} found. No directories to delete.'
        fi
        """,
        ssh_client=ssh_client,
    )

    print(colored("Deployment successful", "green"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "server_name",
        help=f"The name of the server to deploy, among: [{",".join(SERVERS.keys())}]",
    )
    parser.add_argument(
        "--branch",
        nargs="?",
        help="The branch used to pull the code. Default to the server's `default_branch`.",
    )
    parser.add_argument(
        "--skip-front-build",
        help="If passed, do not build fresh front-end files in frontend/dist.",
        action="store_true",
    )
    parser.add_argument(
        "--celery-no-restart",
        help="If passed, do not restart tsosi_celery and tsosi_celery_beat services.",
        action="store_true",
    )
    args = parser.parse_args()
    deploy(
        args.server_name,
        args.branch,
        args.skip_front_build,
        args.celery_no_restart,
    )
