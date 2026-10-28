---
name: ssh-remote-ops
description: 按用户显式提供的连接参数做 SSH 远程操作。未填写必填项时保持 setup_required，不默认连接。
---

# SSH 远程运维

- 上游：classfang/ssh-mcp-server
- commit：7588cab17b562d5a592e53085a4aa5aaec25bf2b
- 版本：1.10.0
- 许可证：ISC
- argv 固定到 @fangjunjie/ssh-mcp-server@1.10.0，禁止 @latest

所有连接值都必填且无默认值。上游写明 --ssh-config-file 默认是 ~/.ssh/config，所以本包始终传入用户给出的配置文件。不要读取本机 SSH config、私钥或凭据，不要默认连接。

不传入 --password、--passphrase、--agent 或 --pre-connect。白名单和远端路径允许列表也必填，因为上游在未设置时允许任意命令和任意远端路径。
