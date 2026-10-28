---
name: setup
description: Check the pinned DingTalk Workspace CLI dws 1.0.64 and reuse or start OAuth. Functional mapping of prototype 钉钉, not a Kimi package and not an MCP server.
---

# 设置钉钉 dws（钉死 v1.0.64）

这是原型「钉钉」的 functional_mapping，不是 Kimi 原包，也不是钉钉官方发布的 Omni 插件。没有 `dws mcp` 子命令。业务命令以 `../cli/SKILL.md` 和本机 `dws <product> --help` 为准。

上游 Z.ai setup 原文在 `provenance/skills/setup/SKILL.md`。原文的 shell 安装器指向 `main`，npm 备选是 `@latest`。本包装两者都不用。

## 1. 检查或安装固定 Windows zip

```bash
dws version
```

Windows 上若没有该命令，用 `Get-Command dws`。缺失时不要运行 `install.sh`，不要执行 `npm install -g dingtalk-workspace-cli@latest`。把固定 zip 交给用户自行安装，解压前核对 sha256。本 skill 不下载、不代装。

- Windows amd64: `https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/download/v1.0.64/dws-windows-amd64.zip`
- sha256: `c037bd1a66d50d8427b446ae479e60b8548600f0b5296c0d90d97c8ab898bdd6`
- Windows arm64: `https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/download/v1.0.64/dws-windows-arm64.zip`
- sha256: `031ff7199d001271de8d1863d092a125bf1bbb020d0f878a56e3f812f93c80c1`
- 来源 commit: `e2c0cdf97e016ee76687d9c26986c23a26a84738`
- 校验文件: `plugin-source-staging/k2/upstream-checksums/dws-v1.0.64-checksums.txt`

安装后再次运行 `dws version`。不是 v1.0.64 就停止业务操作。不要运行 `dws upgrade`。

## 2. 认证

先查状态。已登录就复用，不重新授权。

```bash
dws auth status --format json
dws profile list --format json
```

必须读 `authenticated`。退出码 0 或 `success: true` 不等于已登录。多账号只用用户给出的 `corpId:userId`。

缺少认证时：

```bash
dws auth login
```

无浏览器环境：

```bash
dws auth login --device
```

组织管理员可能要先开 CLI 访问。不要把 OAuth Token、App Secret 或 PAT 放进命令参数或聊天。不要输出环境变量值。

## 3. 上游 Skills

本包的 `cli` 与 `setup` 已够调用 CLI。只有用户单独要求时才看：

```bash
dws skill setup --help
```

先预览目标目录并确认，不默认安装全局 Skills。

插件安装不等于登录成功，也不等于业务写操作已授权。
