---
name: tiktok-for-business
description: 创建、管理与分析 TikTok 广告。未配置 Access-Token 时不要调用接口，也不要把未连接账户说成已投放。
---

# TikTok for Business

原型行是「TikTok for Business」，功能是「创建、管理与分析 TikTok 广告」。本包调用 TikTok Marketing API `v1.3`，不是 Content Posting API，不是其他广告平台，也不是 Kimi 原生产品。

合同钉在 https://github.com/tiktok/tiktok-business-api-sdk 的 commit `f809c396520df2d7b201a9ccc5378d822b728ed3`。路径表在 `references/marketing-api.md`。本包不安装官方 SDK，也不创建 TikTok 开发者应用或广告账户。

## 配置

宿主把插件 `user_config` 注入 MCP 环境：

- `access_token` → `TIKTOK_BUSINESS_ACCESS_TOKEN`。必填，无默认。未配置时 MCP 不会启动，CLI `status` 退出码为 2，`unavailable` 为 `credentials_missing`。
- `app_id` → `TIKTOK_BUSINESS_APP_ID`。空白表示未设置。
- `app_secret` → `TIKTOK_BUSINESS_APP_SECRET`。空白表示未设置。
- `advertiser_id` → `TIKTOK_BUSINESS_ADVERTISER_ID`。空白表示未设置。

不要读取连接配置文件来猜测这些值，不要发明 token，不要在对话、日志或命令回显中输出 Access-Token、app secret 或 auth_code。

开发者应用在 https://ads.tiktok.com/marketing_api/apps/ 。本包不代用户申请应用。

## 调用

先看本地状态，这不会访问网络：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tiktok_business.py status
```

已安装且宿主能启动 MCP 时，用工具 `tiktok_business_status` 和 `tiktok_business_call`。不要把 `prepare` 的结果说成已经创建或分析了广告。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tiktok_business.py prepare campaign_get --query "{\"advertiser_id\":\"ADVERTISER_ID\"}"
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tiktok_business.py call campaign_get --query "{\"advertiser_id\":\"ADVERTISER_ID\"}"
```

`prepare` 只打印方法和路径，不发送请求。`call` 才会请求 `https://business-api.tiktok.com`。

## 功能边界

创建与管理使用 campaign、adgroup、ad 以及同一 SDK 文档中的 smart_plus campaign、adgroup、ad 创建、读取、更新和状态更新。分析使用 `report_integrated_get`；较大报表使用 `report_task_create`、`report_task_check` 和 `report_task_cancel`。

`campaign_create` 至少需要 `advertiser_id`、`campaign_name`、`objective_type`。其他写操作的字段以官方文档为准，本包不补造投放参数。

读取可以在用户要求查看或分析已有广告时执行。创建、更新、状态变更和用 auth_code 换 token 都是远端写操作或凭证交换；执行前说明广告主、对象和变更，并得到用户确认。用户没有确认时只运行 `prepare` 或 `status`。

`oauth2/access_token/` 的响应里会有新 token。把结果交给用户保存，不要复述 token。换票成功不等于已经创建广告。

官方返回非 0 的 `code` 时原样报告，不要改写成成功。
