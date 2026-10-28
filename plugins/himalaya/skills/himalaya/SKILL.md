---
name: himalaya
description: 用用户已安装的 Himalaya 管理邮件。未配置 HIMALAYA_BIN 时不要启动，也不要连接账户或发送邮件。
---

# 邮件

原型行是「邮件」，描述是「邮件与沟通管理工具」。本包是 Pimalaya Himalaya v2.2.1 的邮件命令适配，不是 Gmail，不是 Kimi 原生产品，也不是聊天或日历套件。Gmail 仍是另一行。

上游是 https://github.com/pimalaya/himalaya ，标签 `v2.2.1`，commit `5b12b2a8c2c253b98f15c46610ad74cba2a182bc`。该 commit 的 README 自称 `CLI to manage emails`。许可证是 MIT OR Apache-2.0，正文在本包 `LICENSE-MIT` 和 `LICENSE-APACHE`。本包不含 Himalaya 程序，也不使用 Himalaya 标志替换原型图标。

命令原文在 `references/usage.md`，摘自同一 commit 的 README Usage。不要运行 README 里的安装脚本。

## 启动

`user_config.himalaya_bin` 必填，无默认，只放到 `HIMALAYA_BIN`。不要搜索 PATH，不要下载 Himalaya，不要代填账户或密码。

`scripts/launch.py` 不用 shell。Windows 上该文件必须是原生 `.exe`；`.bat` 和 `.cmd` 退出码为 2，不启动。未配置、路径不是文件，或没有参数时同样退出码为 2，不启动子进程。配置正确时，参数原样传给该程序，并返回它的退出码。

README 写明每个命令都有自己的 `--help`。查看语法、不读取邮箱的调用是：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py envelope search --help
```

这不是已连接账户，也不是已发送邮件。

## 已记录的邮件命令

同一 README 的 Shared API 例子是：

```text
himalaya mailbox list
himalaya envelope list --page 2
himalaya message read 42
```

这些命令会使用用户自己的 Himalaya 配置并可能连接账户。只有用户明确要求使用已配置账户时才运行。不要自行创建账户，不要读取主目录来猜测配置。

`himalaya message compose --to you@example.org --subject Hello --body Hi --send` 和 `himalaya smtp send` 是 README 里的发送命令。用户没有明确要求发送这封邮件时，不要运行它们。本包的检查不发送邮件，也不连接账户。
