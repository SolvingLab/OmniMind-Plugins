---
name: autodesk-fusion
description: 用社区 MCP 操作已经在本机 Autodesk Fusion 里启动的 AutodeskFusionMCP。未配置或插件未运行时不连接，不安装 Fusion。
---

# Autodesk Fusion 社区 MCP

这是原型「Autodesk Fusion」：社区 MCP 操作本机 Fusion。服务器是 `frankhommers/autodesk-fusion-mcp` tag `v1.6.0`，commit `cbd01e540af425a81913d4e6c0d49e09e723aeb6`。它是 Fusion 里的附加模块，不是 Autodesk 官方发布的 MCP，也不是 Kimi 包。不要换成 CrowdStrike Falcon Fusion 或 Oracle Fusion ERP。

## 谁来启动 Fusion

操作者自己把该 commit 的附加模块放进 Fusion 的 AddIns 目录，文件夹名必须是 `AutodeskFusionMCP`，然后在 Fusion 里运行它。上游 README 写的 Windows 目录是 `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`。本包不复制附加模块，不写这个目录，不安装 Fusion，不启动 Fusion。

插件监听 `http://127.0.0.1:8765/mcp`。这个地址没有写进本包默认值。

## 配置

`user_config.fusion_mcp_url` 没有默认值。未设置时宿主不注册 MCP 服务器。设置时只接受：

```text
http://127.0.0.1:8765/mcp
```

端口如果被操作者改过，仍然必须是 `http://127.0.0.1:<port>/mcp` 或 `http://localhost:<port>/mcp`。不要填云端 URL，不要填 API key。这个插件没有账号配置。

脚本入口：

```text
python scripts/launch.py probe
python scripts/launch.py call get_viewport
python scripts/launch.py call execute_python --allow-cad-write --args "{\"code\":\"...\",\"persistent\":false,\"session_id\":\"omnimind\"}"
```

URL 来自 `--url` 或环境变量 `FUSION_MCP_URL`。两者都空时退出码 2，打印 `setup_required`，不打开套接字。

`probe` 只做 `GET /health` 和 `tools/list`。`call` 对会改设计、视口、脚本或注释锁的工具要求 `--allow-cad-write`，否则退出码 2 且不发送。宿主直连 MCP 时不经过这个写保护；那是操作本机 Fusion 的路径，只有操作者已经启动插件并填了 URL 才会注册。

只调用 `references/tools.md` 里的 14 个名字。协议字段在 `references/protocol.md`。

健康检查同名同版本不能证明 Fusion 正在运行。上游 `test_server.py` 也会返回 `autodesk-fusion-mcp` `1.6.0`。`fusionHostProven` 在本客户端里保持 false。
