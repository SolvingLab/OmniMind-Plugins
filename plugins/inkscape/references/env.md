# Environment

Pinned commit `15fb592dd392f3b8bf1f99389113cf94704e13e4` of `jjjsood/inkscape-mcp-server`.

`INKSCAPE_MCP_WORKSPACE_ROOTS` is required. Upstream has no default, does not create a missing root, and does not fall back to the process cwd or the home directory. This package supplies it only as `${user_config.workspace_roots}`, which also has no default. Unset means the MCP server is not registered (`setup_required`).

Not used:

- `${WORKSPACE_ROOT}` is not a supported plugin variable.
- A drive root, a user profile path, or `${OMNIMIND_PROJECT_DIR}` as a silent sandbox.

| Variable | Upstream default | This package |
|---|---|---|
| `INKSCAPE_MCP_WORKSPACE_ROOTS` | none | `${user_config.workspace_roots}`, no default |
| `INKSCAPE_MCP_LIVE_ENABLED` | `true` | `${user_config.live_enabled}`, default `false` |
| `INKSCAPE_MCP_RAW_ACTION_ENABLED` | `false` | `${user_config.raw_action_enabled}`, default `false` |

Windows list separator is `;`.

Runtime dependencies of the upstream package, not of plugin install: Python `>=3.12`, `fastmcp>=3.0,<4.0`, `lxml>=5.0`, `pillow>=10.0`, and `uvx` to launch the git pin. Inkscape on `PATH` is required for render, export, and path geometry only.

This package did not run uv, pip, or the server.
