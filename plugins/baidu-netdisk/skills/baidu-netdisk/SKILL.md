---
name: baidu-netdisk
description: 管理用户自己的百度网盘云端文件与资料。未配置 access_token 时不要连接账户，也不要列出、上传或删除文件。
---

# 百度网盘

原型行是「百度网盘」，描述是「云端文件与资料管理」。本包只对接百度网盘开放平台，不是 Google Drive，不是 WPS 云文档，不是 bypy，也不是百度智能云。

官方文档入口：https://pan.baidu.com/union/doc/ 。接口表在 `references/openapi.md`。

## 配置

宿主把 `user_config` 放进环境变量后再调用脚本。不要读取其它连接配置，不要搜索主目录，不要发明 token。

| user_config | 环境变量 | 何时需要 |
| --- | --- | --- |
| access_token | BAIDU_NETDISK_ACCESS_TOKEN | 列出、搜索、容量、上传、下载、管理文件 |
| app_key | BAIDU_NETDISK_APP_KEY | 只用用户自己的应用换码时 |
| secret_key | BAIDU_NETDISK_SECRET_KEY | 换码或刷新时 |
| redirect_uri | BAIDU_NETDISK_REDIRECT_URI | 授权码模式时，必须与申请 code 时一致 |
| refresh_token | BAIDU_NETDISK_REFRESH_TOKEN | 刷新时。官方说明只能使用一次 |
| app_dir | BAIDU_NETDISK_APP_DIR | 可选。设置后，变更类路径必须落在该 `/apps/{应用名}` 目录下 |

未配置 `access_token` 时，插件清单里的官方 MCP 会被宿主禁用。这是未连接，不是空网盘。

个人使用官方 MCP 时，不需要自建应用。先打印官方授权页，让用户自己登录，再把地址栏里的 access_token 写入 user_config。不要把 token 写入仓库、日志或结果文件。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py authorize-url --mode official-mcp
```

这条命令只打印 URL，不返回 token，也不连接网盘。

## 入口

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py status
```

没有 token 时退出码为 2，`state` 为 `unavailable`，`upstreamCalled` 为 false。不要把这个结果说成已经列出文件。

有 token 时，`status` 会调用官方用户信息和容量接口。只有两条都返回 errno 0 才是这次读取成功。这仍然不是 Main 的原生验收。

## 读取

用户明确要求查看自己的百度网盘时才运行：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py quota
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py list --dir /
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py search --key 资料 --dir / --category 4 --recursion
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py meta --fsid 123 --dlink
```

`category` 4 是官方文档中的文档类型。搜索关键字最多 30 个字符。

## 变更

复制、移动、重命名、删除、建目录、上传和下载都会改变云端或本地文件。用户没有明确要求这一次变更时，不要加 `--yes`。没有 `--yes` 时脚本不发请求。

官方说明第三方应用的管理、上传和下载范围在 `/apps/{应用名}`。不在该前缀下的变更会被本地拒绝。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py mkdir --path /apps/示例/资料 --yes
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py upload --local 报告.pdf --path /apps/示例/报告.pdf --yes
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py download --fsid 123 --output 报告.pdf --yes
```

上传按官方预上传、分片上传、创建文件三步执行。普通用户分片固定为 4 MB，本包按 4 * 1024 * 1024 字节切分。只上传预上传返回的 `block_list` 序号，`partseq` 使用该序号。某一片失败、域名无效或返回的 MD5 与预上传 `block_list` 不一致时，不调用创建文件。续传使用同一次失败返回的 `uploadid`，不要另开任务：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/netdisk.py upload --local 报告.pdf --path /apps/示例/报告.pdf --uploadid <uploadid> --yes
```

同一次调用最多创建文件一次。没有 token 时上传仍是未连接，不是已验收。

## 官方 MCP

`plugin.json` 按官方自定义接入页把 SSE 设为 `https://mcp-pan.baidu.com/sse`，鉴权头是 `Authorization: Bearer ${user_config.access_token}`。宿主只有在 token 已配置时才会启用它。不要把未启用说成已连接。官方建议第一次调用用容量或用户信息，不要先移动、覆盖或分享。
