# Environment

Pinned commit `3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46`. Facts are from that commit's `pyproject.toml`, `README.md`, `LICENSE`, and `src/rhino_mcp/server.py`.

| Variable | Upstream default | This package |
|---|---|---|
| `RHINO_MCP_TRANSPORT` | `stdio` | fixed `stdio` |
| `RHINO_MCP_FORCE_MODE` | auto | `${user_config.force_mode}`, no default |

Unset `force_mode` disables the MCP server. Do not treat auto as already connected.

Not set here, so this package does not point them at a user profile or a drive root:

- `RHINO_HOST` / `RHINO_PORT` upstream default `localhost:4242` for TCP bridge
- `RHINO_MCP_PIPE` upstream default `rhino_mcp` when named-pipe transport is selected
- `RHINO_MCP_SOCKET`
- `RHINO_MCP_TRANSPORT_KIND`

Windows: named pipe is optional and needs `pywin32` only if that transport is used. DBus is not this server's Windows path. The C# plugin location in the README is `%APPDATA%/McNeel/Rhinoceros/8.0/Plug-ins/rhino-mcp/rhino-mcp.rhp`. This package does not create that file.

Runtime, not plugin install: `uvx`, Python `>=3.11`, and the git pin's Python dependencies. Rhino 8 and .NET 8 SDK are not installed here. Bridge stays unconfigured until the operator sets `force_mode=bridge` and has their own Rhino session.
