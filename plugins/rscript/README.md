# rscript

Functional mapping of prototype Rscript to Posit's `mcp-repl` persistent R session. Not an official R plugin, not a Kimi package, and not the R library `mcpr`.

Pinned source: `posit-dev/mcp-repl` tag `v0.3.0` commit `0c4fd352aff1f61273d048aa90d877897ce73315`. Cargo package `mcp-repl` 0.3.0, `publish = false`. Binary `mcp-repl` is `src/main.rs`. `posit-mcp-repl` is a feature-gated alias.

stdio command, not executed here:

```text
mcp-repl --interpreter r --sandbox workspace-write --oversized-output files
```

`R_HOME` comes only from `${user_config.r_home}` and has no default. Unset disables the server. This package does not hardcode a user path or a drive root.

The binary is not inside this wrapper, and this package does not install R, Rust, or `mcp-repl`. A `mcp-repl` already on `PATH` is not this commit. Setup, recorded only and not executed, is `cargo install --git https://github.com/posit-dev/mcp-repl --rev 0c4fd352aff1f61273d048aa90d877897ce73315 --locked --bin mcp-repl`. Do not use `releases/latest` or bare `uvx posit-mcp-repl`; those pins were not verified against this commit.

## Icon

`assets/icon.svg` is the unmodified R logo from https://www.r-project.org/logo/Rlogo.svg. © 2016 The R Foundation. This copy is distributed under CC-BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). The R Foundation also offers GPL-2; that option was not selected because this wrapper is not a GPL-2 work. No changes were made. The logo is not relicensed to Apache-2.0, and using it does not make this package an official R plugin. sha256 `6d3318a61b6370799dc413c8bded66ee3417509c0f4a82c7739e5e1c057c4269`.

README says Windows R support is experimental. This package does not claim a Windows runtime pass.
