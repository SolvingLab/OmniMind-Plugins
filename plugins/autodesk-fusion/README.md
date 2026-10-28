# autodesk-fusion

社区 MCP 操作本机 Fusion。

固定源是 `frankhommers/autodesk-fusion-mcp` tag `v1.6.0` commit `cbd01e540af425a81913d4e6c0d49e09e723aeb6`。MCP 服务器跑在 Autodesk Fusion 附加模块里，Streamable HTTP，地址由操作者填入 `user_config.fusion_mcp_url`。上游文档写的是 `http://127.0.0.1:8765/mcp`。本包不把该地址写成默认值，不安装 Fusion，不把附加模块复制进 `%APPDATA%`。

`scripts/launch.py` 是可调用的标准库客户端。它只连接本机 `/mcp`，先核对 `GET /health` 的 `server=autodesk-fusion-mcp` 和 `version=1.6.0`，再用该 commit 文档里的 `2026-07-28` 无握手请求列出或调用工具。连接失败、身份不符或重定向都不会继续调用工具。

这不是 Autodesk 官方插件，不是 CrowdStrike Falcon Fusion，也不是 Oracle Fusion ERP。

图标是该 commit 的 `commands/mcpAbout/resources/64x64.png`，随仓库 MIT 许可证分发。它不是从 Autodesk 品牌门户取得的商标授权文件。
