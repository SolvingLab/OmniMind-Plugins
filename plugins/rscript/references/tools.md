# R surface at 0c4fd352aff1f61273d048aa90d877897ce73315

Copied from that commit's README. Not invented.

MCP surface:

- tool `repl`
- example input: `{ "input": "1+1\n", "timeout_ms": 10000 }`
- with `--interpreter r`, `repl` sends code to the persistent embedded R session
- interrupt: prefix input with `\u0003`
- reset: prefix input with `\u0004`

README says the exact `repl` description depends on interpreter and `--oversized-output`. Guides in `docs/tool-descriptions/` were not fetched. Do not invent additional tool names.

This is not `Rscript -e` and not `devOpifex/mcpr`.
