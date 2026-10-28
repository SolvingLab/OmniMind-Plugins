# Tools

Names and limits are from README.md at 15c8e33353546148acc2d8bd784551cf3905d1e2, section MCP Server API. The server was not executed and no database was contacted.

- list_schemas: Lists schemas. README does not separately say this tool writes.
- list_objects: Lists objects in a schema. README does not separately say this tool writes.
- get_object_details: Describes one object. README does not separately say this tool writes.
- execute_sql: README: read-only limitations when connected in restricted mode.
- explain_query: Execution plan, including hypothetical indexes. README does not say it creates indexes.
- get_top_queries: Slow queries from pg_stat_statements.
- analyze_workload_indexes: Recommends indexes. README does not say it applies them.
- analyze_query_indexes: Recommends indexes for up to 10 queries. README does not say it applies them.
- analyze_db_health: Health checks. README does not separately say this tool writes.

Mode text:

- Restricted Mode: Limits operations to read-only transactions and imposes constraints on resource utilization (presently only execution time).
- To use restricted mode, replace `--access-mode=unrestricted` with `--access-mode=restricted` in the configuration examples above.
- execute_sql: Executes SQL statements on the database, with read-only limitations when connected in restricted mode.
- Restricted mode is limited to read-only operations, and we limit query execution time to prevent long-running queries from impacting system performance.

Documented examples pass --access-mode=unrestricted. This package always passes --access-mode=restricted. Do not drop that argument. Do not describe a stronger guarantee than the sentences above.
