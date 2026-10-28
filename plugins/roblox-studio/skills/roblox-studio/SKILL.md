---
name: roblox-studio
description: 读取已打开的 Roblox Studio 场景和脚本，修改脚本、插入资源，并控制试玩。
---

# Roblox Studio 官方内置 MCP

服务器在 Roblox Studio 里，通过 stdio 与客户端通信。本包只记录官方文档里的 Windows 启动形式：`cmd.exe /c` 加上你自己填写的启动器路径。未填写时不连接。本包不打开 Studio，不改 Studio 设置，不读取本机安装版本。

启用方式写在文档里：打开 Assistant，进入 Manage MCP Servers，打开 Enable Studio as MCP server。那是操作者在 Studio 里做的事，本卡没有执行。

每次工具调用都要带 `studio_id`。先用 `list_roblox_studios` 查看已连接的实例。工具名只使用 `references/tools.md`。
