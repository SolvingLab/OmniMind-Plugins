# 百度网盘开放平台接口

Fetched 2026-10-15 with HTTPS certificate verification. These are the calls this adapter makes. They are not a copy of the official manuals.

User-Agent on official examples is `pan.baidu.com`. Scope for authorization is `basic,netdisk`.

| Operation | Method and URL | Doc |
| --- | --- | --- |
| Authorization-code page | GET `https://openapi.baidu.com/oauth/2.0/authorize` `response_type=code` | https://pan.baidu.com/union/doc/使用入门/接入授权/授权码模式/ updated 2022-03-22 |
| Code, refresh, device token | GET `https://openapi.baidu.com/oauth/2.0/token` | same page, and device-code page updated 2022-04-13 |
| Device code | GET `https://openapi.baidu.com/oauth/2.0/device/code` `response_type=device_code` | https://pan.baidu.com/union/doc/使用入门/接入授权/设备码模式授权/ |
| User info | GET `https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo` | https://pan.baidu.com/union/doc/基础网盘服务/获取用户信息/获取用户信息/ updated 2026-09-08 |
| Quota | GET `https://pan.baidu.com/api/quota` | https://pan.baidu.com/union/doc/基础网盘服务/获取网盘容量信息/ updated 2026-09-08 |
| List | GET `https://pan.baidu.com/rest/2.0/xpan/file?method=list` | https://pan.baidu.com/union/doc/基础网盘服务/获取文件信息/获取文件列表/ updated 2026-09-02 |
| Keyword search | GET `https://pan.baidu.com/rest/2.0/xpan/file?method=search` | https://pan.baidu.com/union/doc/基础网盘服务/获取文件信息/搜索文件关键词搜索/ updated 2026-09-08 |
| Meta by path | GET `https://pan.baidu.com/rest/2.0/xpan/file?method=meta` | https://pan.baidu.com/union/doc/基础网盘服务/获取文件信息/查询文件信息/ updated 2026-09-02 |
| Meta by fsid | GET `https://pan.baidu.com/rest/2.0/xpan/multimedia?method=filemetas` | same page |
| Copy, move, rename, delete | POST `https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager` | https://pan.baidu.com/union/doc/基础网盘服务/管理文件/ updated 2026-09-09 |
| Make directory | POST `https://pan.baidu.com/rest/2.0/xpan/file?method=create` with `isdir=1` | https://pan.baidu.com/union/doc/基础网盘服务/创建文件夹/ updated 2026-09-09 |
| Precreate | POST `https://pan.baidu.com/rest/2.0/xpan/file?method=precreate` | https://pan.baidu.com/union/doc/基础网盘服务/上传/预上传/ updated 2026-09-09 |
| Locate upload host | GET `https://d.pcs.baidu.com/rest/2.0/pcs/file?method=locateupload` `appid=250528` `upload_version=2.0` | https://pan.baidu.com/union/doc/基础网盘服务/上传/获取上传域名/ updated 2026-09-09 |
| Upload slice | POST `https://<returned-host>/rest/2.0/pcs/superfile2?method=upload&type=tmpfile` with the precreate `block_list` index as `partseq` | https://pan.baidu.com/union/doc/基础网盘服务/上传/分片上传/ updated 2026-09-09 |
| Finish upload | POST `https://pan.baidu.com/rest/2.0/xpan/file?method=create` with `isdir=0` | https://pan.baidu.com/union/doc/基础网盘服务/上传/创建文件/ updated 2026-09-09 |
| Download | filemetas `dlink=1`, then GET the https dlink with the access token | https://pan.baidu.com/union/doc/基础网盘服务/下载/ updated 2026-09-02 |
| Official MCP SSE | `https://mcp-pan.baidu.com/sse` with `Authorization: Bearer` | https://pan.baidu.com/union/doc/mcp-server/操作指南/在-agent-中自定义使用/ updated 2026-07-28 |

The slice page, fetched again on 2026-10-15, says an ordinary-user slice is fixed at 4 MB, a file of at most 4 MB is one upload, and only the indexes in the precreate `block_list` are uploaded. Non-final slices must reach that size (errno 31299). The page does not print a decimal byte count; this adapter uses `4 * 1024 * 1024`. Create runs once, after those slices succeed, and uses MD5 values in partseq order. A slice error does not call create. Resume sends the same `uploadid` on precreate and still creates at most once.

The file-manager page says `method=filemanager` and `method=meta` only reach `/apps/{appname}`. The download page says a third-party app has one folder under `/apps`. Public error `-6` means authentication failed.

The official Python SDK intro, updated 2022-06-16, lists the same xpan methods and says the SDK is a console download with an incomplete requirements file. This package does not vendor that zip.

https://pan.baidu.com/union/doc/sdk/python/python-sdk使用入门/
