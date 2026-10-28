# NetSuite

原型「NetSuite」的本地适配，描述保持「连接 NetSuite ERP」。只向用户自己的账户专属 SuiteTalk REST 发送 OAuth 2.0 client-credentials 令牌请求，并读取 `GET /services/rest/record/v1/metadata-catalog`。不创建集成记录，不写 ERP，不使用 TBA，也不使用 NetSuite 标志。

官方说明见 `skills/netsuite/references/contract.md` 和 `SOURCE.json`。许可证是 Apache-2.0，见 `LICENSE`。适配作者不是 Oracle。

入口是 `node scripts/launch.mjs connect`。六个 `NETSUITE_*` 配置缺任一时退出码为 2，不发请求。协议检查使用本机合成密钥和注入的传输，不是 NetSuite 在线通过。
