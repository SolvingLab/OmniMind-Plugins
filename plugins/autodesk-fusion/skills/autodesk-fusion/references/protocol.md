# 固定协议

来源是 `frankhommers/autodesk-fusion-mcp` tag `v1.6.0` commit `cbd01e540af425a81913d4e6c0d49e09e723aeb6`。

- 插件在 Autodesk Fusion 进程内启动，只绑定 `127.0.0.1`。
- `settings.py` 里 `MCP_SERVER_PORT = 8765`。README 写的客户端地址是 `http://127.0.0.1:8765/mcp`。
- `GET /health` 返回 `server` `autodesk-fusion-mcp`、`version` `1.6.0`。`git_commit` 由插件运行时另填，可以为空。
- `POST /mcp` 同时接受无握手的 `2026-07-28`，以及 `2025-11-25`、`2025-06-18`、`2025-03-26` 的 `initialize`。本客户端只用 `2026-07-28`。
- 本客户端不发送 `Origin`。上游写明原生客户端可以省略；带了就必须等于 `http://127.0.0.1:<port>` 或 `http://localhost:<port>`。
- 不跟随 3xx。不连接非本机主机。不使用 `https`、用户信息、query 或 fragment。
- `tools/call` 的现代路径用 `text/event-stream`，校验错误可以先回 `application/json`。两者都要带 `resultType: complete`。

`2026-07-28` 的 `tools/list` 请求头是 `Content-Type: application/json`、`Accept: application/json, text/event-stream`、`MCP-Protocol-Version: 2026-07-28`、`Mcp-Method: tools/list`。正文 `params._meta` 必须有 `io.modelcontextprotocol/protocolVersion` 和 `io.modelcontextprotocol/clientCapabilities`。`tools/call` 还要有与 `params.name` 相同的 `Mcp-Name`。

这个端点没有账号，也没有云端 Fusion Automation API。缺 URL 时宿主不注册服务器。
