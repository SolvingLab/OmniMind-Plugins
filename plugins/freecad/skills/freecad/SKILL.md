---
name: freecad
description: 在 FreeCAD 里新建和查看 CAD 文档、创建和修改零件与模型，并在已启动的插件上运行建模脚本。
---

# FreeCAD MCP 0.1.27

这是社区仓库 `neka-nat/freecad-mcp` 的两个组件，不是 Kimi 包。

1. FreeCAD addon：`addon/FreeCADMCP`，工作台类名 `FreeCADMCPAddonWorkbench`，显示名 `MCP Addon`。`package.xml` 版本 `0.1.27`。操作者自己把这个目录复制进 FreeCAD 的 Mod 目录，重启后在工具栏启动 RPC。本包不复制、不启动。
2. stdio 服务器：`freecad_mcp.server:main`。宿主命令是带固定 commit 的 `uvx --from git+https://github.com/neka-nat/freecad-mcp.git@78bf0230a03324b56c9a0b7f55150fb5be2a0d42 freecad-mcp --host ${user_config.rpc_host}`。

`rpc_host` 未设置时服务器不注册。这是 `setup_required`。端口 `9875` 写在该 commit 的 `get_freecad_connection()` 里，没有 `--port` 参数。

Windows 上 addon 目录以该 commit 的 `docs/installation.md` 为准：FreeCAD 1.1 是 `%APPDATA%\FreeCAD\v1-1\Mod\`，更早的未分版本安装是 `%APPDATA%\FreeCAD\Mod\`。本包不写入这些路径。同一文档还记录了部分 Windows 客户端启动 Python 入口时的 `EFTYPE` / `uv_spawn`，那是客户端问题，不是本包已验证的连接。

只调用 `references/tools.md` 里从 `server.py` 摘出的名字。
