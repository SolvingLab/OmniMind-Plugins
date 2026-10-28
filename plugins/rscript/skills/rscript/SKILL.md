---
name: rscript
description: Use Posit mcp-repl 0.3.0 as a persistent R session for prototype Rscript. Not one-shot Rscript -e, not the mcpr library, not official R, not Kimi.
---

# Rscript via mcp-repl 0.3.0

这是原型「Rscript」的 functional_mapping。真实通道是 `posit-dev/mcp-repl` commit `0c4fd352aff1f61273d048aa90d877897ce73315` 的持久 R 会话，不是一次 `Rscript -e`，也不是 `devOpifex/mcpr` 那种 R MCP 库。

## 启动命令

宿主启动的是二进制 `mcp-repl`，参数来自该 commit 的 README：

```text
mcp-repl --interpreter r --sandbox workspace-write --oversized-output files
```

`--interpreter r` 锁在 R。README 的解析顺序是命令行、然后 `MCP_REPL_INTERPRETER`、再默认 `r`。本包两处都写成 `r`，避免落到 Python。Python 在 README 里不是 Windows 的稳定面。

`user_config.r_home` 没有默认值，映射到 `R_HOME`。未设置时宿主不注册服务器，状态是 `setup_required`。不要填盘符根，不要写死本机 profile。未设置 `R_HOME` 时上游会从 `PATH` 上的 `R RHOME` 发现 R；本包装不采用那条隐式发现，以免没配置也启动。

## 安装二进制和安装本插件不是一回事

本目录不包含 `mcp-repl` 可执行文件，也不安装 R 或 Rust。操作者若要连接，需自行准备与该 commit 相同的二进制，例如：

```text
cargo install --git https://github.com/posit-dev/mcp-repl --rev 0c4fd352aff1f61273d048aa90d877897ce73315 --locked --bin mcp-repl
```

K4 没有执行这条命令，也没有运行 `scripts/install.ps1`，没有安装 R、Rust 或 `mcp-repl`。PATH 上已有的 bare `mcp-repl` 不能当成 commit `0c4fd352aff1f61273d048aa90d877897ce73315`。上面的 cargo 行只是 setup 记录，没有全局执行。`Cargo.toml` 写了 `publish = false`。README 提到 PyPI 名 `posit-mcp-repl` 和 `releases/latest`，都没有核对本 commit，不能当固定来源。

## 真实 R 工具

README 的 MCP surface 是 `repl`，输入形如 `{ "input": "1+1\n", "timeout_ms": 10000 }`。在 `--interpreter r` 下，这是送给持久 R 会话的代码，不是计算器演示包。中断前缀是 `\u0003`，重置前缀是 `\u0004`。更细的工具说明在未拉取的 `docs/tool-descriptions/repl_tool_r.md`。

## 沙箱和 Windows

README 写默认沙箱是 `workspace-write`，网络关闭，写入限制在 workspace roots 和会话临时目录。`docs/sandbox.md` 这次没读，所以具体根目录列表是 UNKNOWN。本包没有追加盘符根，也没有把工作目录写成用户主目录。

README 写 Windows 上 R 是 experimental。不要把这个包装说成 Windows R 已验证。
