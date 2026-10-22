from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    name: str
    address: str
    user: str
    default_branch: str = field(default="main")
    # Vite mode of the frontend build, i.e. the `frontend/.env.{mode}` file used.
    frontend_mode: str = field(default="production")


SERVERS = {
    "prod": ServerConfig(name="prod", address="tsosi.u-ga.fr", user="deployer"),
    "dev": ServerConfig(
        name="dev",
        address="tsosi-dev.u-ga.fr",
        user="deployer",
        default_branch="dev",
        frontend_mode="dev-server",
    ),
}


def get_server(name: str) -> ServerConfig:
    return SERVERS[name]
