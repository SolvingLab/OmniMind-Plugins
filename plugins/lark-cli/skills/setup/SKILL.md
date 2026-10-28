---
name: setup
description: Check the pinned Lark CLI 1.0.98, reuse an existing profile, or guide OAuth. This is a functional mapping of prototype 飞书, not a Kimi package and not an MCP server.
---

# 设置 Lark CLI（钉死 v1.0.98）

这是原型「飞书」的 functional_mapping，不是 Kimi 原包，也不是飞书官方发布的 Omni 插件。没有 `lark-cli mcp` 子命令。业务命令以同目录 `../cli/SKILL.md` 和本机 `lark-cli <domain> --help` 为准。

上游 Z.ai setup 原文在 `provenance/skills/setup/SKILL.md`。原文使用 `npm install -g @larksuite/cli@latest`，本包装不采用 `@latest`。

## 1. 检查或安装固定版本

```bash
lark-cli --version
```

Windows 上若没有该命令，用 `Get-Command lark-cli`。缺失时不要执行 npm、npx 或 `@latest`。把下面的固定包交给用户自行安装，并在解压前核对 sha256。本 skill 不下载、不代装。

- Windows amd64: `https://github.com/larksuite/cli/releases/download/v1.0.98/lark-cli-1.0.98-windows-amd64.zip`
- sha256: `b13a5d710f9afe327b34bfe68c4a736a574d4d97274f6da862e912dfada1ccdc`
- Windows arm64: `https://github.com/larksuite/cli/releases/download/v1.0.98/lark-cli-1.0.98-windows-arm64.zip`
- sha256: `6a111ccfed1f89eca95fbf7a9ef0ae941b9017409a864bf6cd93becc430dc810`
- 来源 commit: `ac81f5056ab88f37d581d25916f3dab85abfca76`
- 校验文件: `plugin-source-staging/k2/upstream-checksums/lark-v1.0.98-checksums.txt`

安装后再次运行 `lark-cli --version`。版本不是 1.0.98 就停止业务操作。官方 `npx @larksuite/cli@latest install` 和 `lark-cli update` 会改全局 Skills，不使用。

## 2. 复用身份

用户指定 `--profile <name>` 时，后续命令保留它。

```bash
lark-cli auth status --json --verify
```

只看 `identity`、`verified`、`identities.user.status`、`userName`、`openId`、`tokenStatus`。不读取、不输出 App Secret、OAuth Token、Cookie 或配置文件。

- `not_configured`：进入第 3 步。
- 用户身份不存在或授权失效：进入第 4 步。
- `identity=user` 且服务端验证成功：进入第 5 步。
- 只有 bot 可用不能当成用户已登录。

## 3. 应用配置

用户确认后才运行：

```bash
lark-cli config init --new
```

把授权 URL 原样展示。不要猜 App ID 或 Secret。工具看不到终端输出时，让用户在自己的终端运行。

## 4. OAuth

先从目标命令帮助确定最小 scope。不要把 Token 或 Secret 贴进聊天。

```bash
lark-cli auth login --scope <required-scopes> --no-wait --json
lark-cli auth login --device-code <device-code>
```

展示链接后结束本轮，等用户回来再完成 device code。

## 5. 最小只读验证

```bash
lark-cli auth check --scope <required-scopes> --json
lark-cli calendar +agenda --as user --format json
```

日历只是上游示例。没有日历任务时，改用当前任务的最小只读命令。成功标准是退出码 0 且 JSON `ok == true`。写操作仍按 `../cli/SKILL.md` 先确认。

插件安装不等于登录成功，也不等于业务请求成功。
