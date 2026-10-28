# inkscape

Functional mapping of prototype Inkscape. Not an official Inkscape plugin and not a Kimi package.

Pinned source: `jjjsood/inkscape-mcp-server` commit `15fb592dd392f3b8bf1f99389113cf94704e13e4`.

That commit's README and `pyproject.toml` project URLs say `https://github.com/jjjsood/inkscape-mcp`. That URL is wrong. The repo that exists is `https://github.com/jjjsood/inkscape-mcp-server`.

There is no PyPI release of this commit. Do not use bare `uvx inkscape-mcp`.

stdio command, not executed by this package:

```text
uvx --python 3.12 --from git+https://github.com/jjjsood/inkscape-mcp-server.git@15fb592dd392f3b8bf1f99389113cf94704e13e4 inkscape-mcp
```

`--python 3.12` is uv's own option. `pyproject.toml` says `requires-python = ">=3.12"`. The console script is `inkscape-mcp = "inkscape_mcp.server:main"`.

`INKSCAPE_MCP_WORKSPACE_ROOTS` has no default. This package passes only `${user_config.workspace_roots}`. If that option is unset, the host does not register the server. That is `setup_required`. It does not fall back to a drive root, a user profile, or `${WORKSPACE_ROOT}`.

Installing this directory does not install uv, Python, Inkscape, fastmcp, lxml, or pillow, and it does not start MCP.

Icon: no bitmap in this package. I binds the existing vector/pencil semantic icon. This file is not that binding.
