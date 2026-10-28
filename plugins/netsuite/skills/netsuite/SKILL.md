---
name: netsuite
description: 连接 NetSuite ERP。用用户自己的 OAuth 2.0 客户端证书访问账户专属 SuiteTalk REST。未配置时不要启动，也不要创建集成记录或写入 ERP。
---

# NetSuite

原型行是「NetSuite」，描述保持「连接 NetSuite ERP」。本目录是本地适配，不是 Oracle 或 NetSuite 发布的插件，也不是其他 ERP。

官方接口是 SuiteTalk REST Web Services。本适配只做 OAuth 2.0 客户端证书（client credentials）连接，然后读取 metadata-catalog。不使用 TBA，不打开浏览器，不执行 SuiteQL，不创建、更新或删除记录。

## 启动

六个配置都必填，没有默认值。不要把私钥、client ID 或 certificate ID 放进命令行、聊天或日志：

- `user_config.netsuite_account_id` 只展开到 `NETSUITE_ACCOUNT_ID`
- `user_config.netsuite_suitetalk_url` 只展开到 `NETSUITE_SUITETALK_URL`
- `user_config.netsuite_client_id` 只展开到 `NETSUITE_CLIENT_ID`
- `user_config.netsuite_certificate_id` 只展开到 `NETSUITE_CERTIFICATE_ID`
- `user_config.netsuite_jwt_alg` 只展开到 `NETSUITE_JWT_ALG`
- `user_config.netsuite_private_key_pem` 只展开到 `NETSUITE_PRIVATE_KEY_PEM`

账户 ID 用 NetSuite 里的原样拼写，例如 `123456` 或 `123456_SB1`。SuiteTalk 基址从 Setup > Company > Company Information 的 Company URLs 复制，只保留 origin，例如 `https://123456-sb1.suitetalk.api.netsuite.com`。证书和 client ID 来自用户自己的 OAuth 2.0 integration record，以及 Setup > Integration > Manage Authentication > OAuth 2.0 Client Credentials (M2M) Setup 上的映射。`NETSUITE_JWT_ALG` 必须是该证书对应的 `PS256`、`PS384`、`PS512`、`ES256`、`ES384` 或 `ES512`。

本包不创建账户、集成记录、证书或令牌，也不读取连接配置文件。缺任一配置、主机与账户 ID 的官方变换不一致，或私钥与算法不匹配时，退出码为 2，打印 `setup_required`，不发请求。

```text
node ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.mjs connect
```

成功时退出码为 0，stdout 是一行 JSON：`connected` 为 true，并带有 `recordTypeCount`。不打印 access token 或私钥。非 200、重定向或响应缺少官方 `items` 数组时退出码为 1，不跟随 Location，也不把令牌送到其他主机。

请求形状在 `references/contract.md`。安装本包不是已连接。没有用户自己的 NetSuite 账户和 OAuth 2.0 客户端证书映射时，状态是 setup_required，不是功能通过。
