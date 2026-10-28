# Environment and Windows

From `README.md` and `Cargo.toml` at `0c4fd352aff1f61273d048aa90d877897ce73315`. `docs/sandbox.md` was not read.

| Name | This package |
|---|---|
| `--interpreter` | `r` |
| `MCP_REPL_INTERPRETER` | `r` |
| `R_HOME` | `${user_config.r_home}`, no default |
| `--sandbox` | `workspace-write` as documented for non-Codex clients |
| `--oversized-output` | `files` |

Unset `r_home` disables the server before spawn. No drive root and no owner profile path is written.

Upstream also documents `MCP_REPL_DEBUG_DIR` and `--debug-dir`. This package does not set them.

Windows, from the README: R support is experimental. Python is not the stable Windows surface. Cargo.toml has a Windows target dependency block (`windows`, `windows-sys`); those are build dependencies of the binary, not installed by this plugin.

Runtime, not plugin install: a `mcp-repl` binary from this commit, a Rust toolchain only if the operator builds it, and an R installation identified by `R_HOME`. R is not bundled.
