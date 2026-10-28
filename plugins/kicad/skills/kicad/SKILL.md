---
name: kicad
description: Use the pinned community KiCad MCP server 0.20.1. Functional mapping, not official KiCad and not a Kimi package.
---

# KiCad MCP 0.20.1

这是原型「KiCad」的 functional_mapping。服务器是 `io.github.ProductOfAmerica/mcp-server-kicad`，不是 KiCad 官方包，也不是 Kimi 包。不要调用不存在的 `kicad mcp` 子命令。

宿主通过本包 `.mcp.json` 启动：

```text
uvx --from mcp-server-kicad==0.20.1 mcp-server-kicad
```

不要改成不带 `==0.20.1` 的命令。PyPI wheel `mcp_server_kicad-0.20.1-py3-none-any.whl` sha256 是 `c226461e2b23d8567af4109e41acb60ed879d6a288102177e7e81804ea6af012`。源 commit 是 `511a50d6bf6f1a0df1b2c965443efa674d2fe618`。

## 运行依赖，不是插件安装

- Windows 需要本机 `uvx`，Python `>=3.10`。
- 导出、ERC、DRC 需要用户已安装的 KiCad 9 或 10，以便找到 `kicad-cli`。本包不安装 KiCad。
- 工作目录必须是用户的 KiCad 工程。不要写死路径，不要新建示例工程来冒充连接成功。
- 插件安装不等于 MCP 已启动，也不等于 KiCad 文件已被修改。

## 已核对工具

109 个工具名在 `references/tools.md`，来自该 commit 的 `mcp_server_kicad/{schematic,pcb,project,symbol,footprint}.py`。只调用那里出现的名字。写文件前先说明目标工程和具体工具。
