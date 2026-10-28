---
name: postgresql
description: 用已固定的 crystaldba/postgres-mcp 做 PostgreSQL 助手。安装不等于已连接数据库。
---

# PostgreSQL

- 上游：crystaldba/postgres-mcp
- commit：15c8e33353546148acc2d8bd784551cf3905d1e2
- 版本：0.3.0
- 许可证：MIT
- 入口：postgres-mcp = postgres_mcp:main
- 启动 pin：uvx --python 3.12 --from git+https://github.com/crystaldba/postgres-mcp.git@15c8e33353546148acc2d8bd784551cf3905d1e2 postgres-mcp --access-mode=restricted
- 禁止：uvx postgres-mcp，以及不带 --access-mode=restricted 的启动

user_config.database_uri 必填，无默认值，sensitive。未设置时不要启动 MCP。不要连接真实数据库，不要读取凭据，不要把 localhost 或示例口令写进默认值。

上游 README 对 restricted 的原句：

- Restricted Mode: Limits operations to read-only transactions and imposes constraints on resource utilization (presently only execution time).
- Restricted mode is limited to read-only operations, and we limit query execution time to prevent long-running queries from impacting system performance.
- execute_sql has read-only limitations in restricted mode.

文档示例使用 --access-mode=unrestricted。本包不能省略 restricted 参数，也不把未逐项说明的工具说成比上述原句更强的只读保证。工具名见 references/tools.md。
