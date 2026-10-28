---
name: docker
description: 用已固定的 ckreiling/mcp-server-docker 管理容器、镜像、网络和卷。安装不等于已连接 Docker。
---

# Docker 容器管理

只使用本包已核验的上游工具。不要为了验收本包去执行 docker 服务命令。

- 上游：ckreiling/mcp-server-docker
- commit：57a7df208fdc2362505835f670e53c66f3717c48
- 版本：0.3.0
- 许可证：GPL-3.0
- 入口：mcp-server-docker = mcp_server_docker:main
- 启动 pin：uvx --python 3.12 --from git+https://github.com/ckreiling/mcp-server-docker.git@57a7df208fdc2362505835f670e53c66f3717c48 mcp-server-docker
- 禁止：uvx mcp-server-docker

user_config.docker_host 必填，无默认值。未设置时不要启动 MCP。不要把本机 docker.sock、命名管道、盘符根或用户目录写进默认值。本包不读取本机凭据。

工具名见 references/tools.md。上游写明不支持 privileged 和 cap-add/cap-drop。不要把密钥放进容器配置。
