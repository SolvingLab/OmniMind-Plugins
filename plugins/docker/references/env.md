# Config

user_config.docker_host is required, has no default, and is sensitive.
The host may expand it only into DOCKER_HOST.

If it is unset, do not start this MCP server. Do not preset the local docker socket, a Windows named pipe, a drive root, or a profile path.

Upstream uses Docker SDK from_env. This package does not select an SSH identity file and does not read local credentials.
uvx and docker were not executed.
