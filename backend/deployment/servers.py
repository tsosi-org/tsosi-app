from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    name: str
    address: str
    user: str
    default_branch: str = field(default="main")


SERVERS = {
    "prod": ServerConfig(name="prod", address="tsosi.u-ga.fr", user="deployer")
}


def get_server(name: str) -> ServerConfig:
    return SERVERS[name]
