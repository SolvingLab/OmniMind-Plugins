---
name: rhino
description: Use the pinned community Rhino MCP server rhino3dm-mcp 0.6.0 at commit 3e10efb. Functional mapping, not official McNeel and not Kimi.
---

# Rhino MCP 0.6.0

这是原型「Rhino」的 functional_mapping。服务器是 `EaseHee/rhino-mcp`，commit `3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46`。不是 McNeel 官方插件，也不是 Kimi 包。

## 启动命令

```text
uvx --python 3.11 --from git+https://github.com/EaseHee/rhino-mcp.git@3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46 rhino3dm-mcp
```

入口是该 commit 的 `rhino3dm-mcp = rhino_mcp.server:main`。`server.py` 的 `main` 默认传输是 stdio。本包把 `RHINO_MCP_TRANSPORT` 固定为 `stdio`。不要改成 bare `uvx rhino3dm-mcp`。K4 没有执行这条命令，也没有运行 `rhino-mcp install`。

## 两种模式，bridge 未连接

`user_config.force_mode` 没有默认值。未设置时宿主不注册服务器，状态是 `setup_required`。

- `standalone`：用 `rhino3dm` 处理 `.3dm`，不需要本机 Rhino。这不是已经连上 Rhino。
- `bridge`：README 写明要本机 Rhino 8 里加载 `rhino-mcp.rhp`。本包不安装 Rhino，不编译插件，不启动 Rhino，不写 `%APPDATA%`。把 `force_mode` 设成 `bridge` 只是允许服务器去找桥，不表示桥已经连上。

Windows named pipe 是可选传输。上游默认管道名是 `rhino_mcp`，可选依赖 `pywin32`。本包不安装 `pywin32`，也不把管道名写成用户路径。

## 运行依赖，不是插件安装

- 连接时需要 `uvx` 和 Python `>=3.11`。上游依赖 `mcp[cli]>=1.2,<2`、`pydantic>=2.6,<3`、`rhino3dm>=8.9,<9`，由 uv 在解析 git pin 时安装，不由本插件安装。
- 不要填盘符根，不要造 `${WORKSPACE_ROOT}`。这个服务器的模式开关不是工作区沙箱；文件路径由具体工具参数给出，本包不授予全盘。

工具类别和 README 点名的工具在 `references/tools.md`。只调用那里出现的名字。完整签名文件 `docs/en/tools-reference.md` 这次没有拉取。
