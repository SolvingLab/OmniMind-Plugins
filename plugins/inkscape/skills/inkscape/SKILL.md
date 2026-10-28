---
name: inkscape
description: Use the pinned community Inkscape stdio server at commit 15fb592. Functional mapping, not official Inkscape, not Kimi, and not a PyPI package.
---

# Inkscape MCP 15fb592

这是原型「Inkscape」的 functional_mapping。服务器是 `jjjsood/inkscape-mcp-server`，commit `15fb592dd392f3b8bf1f99389113cf94704e13e4`。不是 Inkscape 官方插件，也不是 Kimi 包。

该 commit 的 README 和 `pyproject.toml` 把仓库写成 `https://github.com/jjjsood/inkscape-mcp`。那是错误 URL。实际仓库是 `https://github.com/jjjsood/inkscape-mcp-server`。

## 启动命令

宿主读 `.mcp.json`，同名时以 `.omnimind-plugin/plugin.json` 的 `mcpServers` 为准。命令是：

```text
uvx --python 3.12 --from git+https://github.com/jjjsood/inkscape-mcp-server.git@15fb592dd392f3b8bf1f99389113cf94704e13e4 inkscape-mcp
```

`--python 3.12` 是 uv 自己的参数，因为该 commit 的 `requires-python` 是 `>=3.12`。入口是 `inkscape-mcp = inkscape_mcp.server:main`。没有这个 commit 的 PyPI release，不要写成 `uvx inkscape-mcp`。K4 没有执行这条命令。

## 安装和运行不是同一件事

- 安装本目录不会安装 uv、Python、Inkscape，也不会安装上游依赖 `fastmcp>=3.0,<4.0`、`lxml>=5.0`、`pillow>=10.0`。
- 读、改、校验、快照不需要 Inkscape 二进制。渲染、导出、路径几何需要用户自己的 Inkscape 在 `PATH` 上。
- `user_config.workspace_roots` 未设置时，宿主不注册这个 MCP server。状态是 `setup_required`。不要填盘符根，不要填用户 profile，不要造 `${WORKSPACE_ROOT}`。Windows 多个目录用 `;` 分隔。
- `live_enabled` 在本包默认 `false`。上游默认是 `true`。本包不连接 GUI。
- 只调用 `references/tools.md` 里从该 commit 源码摘出的名字。环境说明在 `references/env.md`。
