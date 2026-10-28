---
name: tencent-ads
description: 调用腾讯广告 Marketing API v3.0 做智能投放读写。未配置 access_token 或 account_id 时不要请求账户，也不要创建广告。
---

# 腾讯广告智能投放

原型行是「腾讯广告」，功能是「腾讯广告智能投放」。本包是腾讯广告 Marketing API 的可调用适配，不是 TikTok for Business，不是其他广告平台，也不是把 Go SDK 二进制打进包里。

上游 SDK：https://github.com/TencentAd/marketing-api-go-sdk 标签 `v1.7.87`，commit `81d6cc04b58d7d5a5ec9ad0137e43b3b6c52fde9`。该 commit 的 README 称本 SDK 为腾讯广告 Marketing API SDK。许可证 Apache-2.0，正文在本包 `LICENSE`。接口事实在 `references/pinned-interface.json`。

开发者入门页：https://developers.e.qq.com/docs/start ，标题「开发文档 | 开发者专区 - 腾讯广告」。该页写明用 authorization_code 换 token 的地址是 `https://api.e.qq.com/oauth/token`，所有接口用请求参数 `access_token` 鉴权。该页没有写 v3.0 广告组路径；广告组路径以钉选的 v3 SDK 为准。

## 配置

把插件 `user_config` 放进环境变量后再启动脚本。不要搜索主目录，不要读取连接配置，不要编造 token 或 account_id。

| user_config | 环境变量 | 是否必填 |
| --- | --- | --- |
| access_token | TENCENT_ADS_ACCESS_TOKEN | 读广告组时必填 |
| account_id | TENCENT_ADS_ACCOUNT_ID | 读广告组时必填，整数 |
| api_base | TENCENT_ADS_API_BASE | 否。只允许 `https://api.e.qq.com/v3.0` 或 `https://sandbox-api.e.qq.com/v3.0` |
| client_id | TENCENT_ADS_CLIENT_ID | 仅 oauth-token |
| client_secret | TENCENT_ADS_CLIENT_SECRET | 仅 oauth-token |

未配置时：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tencent_ads.py status
```

退出码 2，JSON `state` 为 `setup_required`，`available` 为 false。这不是已投放，也不是已连接账户。

## 已钉选的智能投放接口

v3 SDK `pkg/ads/v3/tencentadsV3.go` 在 Init 时把 host 设为 `api.e.qq.com`，ApiVersion 为 `v3.0`，因此正式环境基址是 `https://api.e.qq.com/v3.0`。`docs/v3/AdgroupsApi.md` 写沙箱基址是 `https://sandbox-api.e.qq.com/v3.0`。

同一文档的方法：

- `GET /adgroups/get` 获取营销单元
- `POST /adgroups/add` 创建营销单元
- `POST /adgroups/update` 更新营销单元

鉴权 query 来自同一 commit 的 `pkg/ads/v3/middleware_auth.go`：`access_token`、`timestamp`、`nonce`。`user_token` 只在非空时附加。nonce 取 UUID 字符串的 `[0:8]+[9:13]+[14:18]`。

`GET /adgroups/get` 的 query 还有 `account_id` 和 `fields`。`fields` 按 SDK 的 multi 格式发 JSON 数组。默认字段包含 `smart_bid_type`、`smart_cost_cap`、`smart_targeting_status`。这些 json 名在同一 commit 的 `pkg/model/v3/model_adgroups_get_list_struct.go`。

创建请求上的智投相关字段，来自同一 commit 的 `AdgroupsAddRequest`：`smart_bid_type`、`smart_cost_cap`、`smart_targeting_mode`、`is_smart_delivery_upgrade_project`。`SmartBidType` 只有 `SMART_BID_TYPE_CUSTOM` 和 `SMART_BID_TYPE_SYSTEMATIC`。`SmartTargetingMode` 的注释是「营销智能定向功能」，钉选值只有 `SMART_TARGETING_MANUAL`。

`SmartDeliveryGoal` 的注释是「场景化投放目标」。枚举在 `references/smart-delivery-goals.json`，共 100 个，摘自 `pkg/model/v3/model_smart_delivery_goal.go`。`SmartDeliverySceneSpec` 含 `smart_delivery_goal`。该 commit 的 `AdgroupsAddRequest` 没有 `smart_delivery_scene_spec` 字段。不要把这个字段发明成另一个 URL。用户正文里如果出现 `smart_delivery_goal`，值必须在钉选枚举内。

## 命令

查看钉选目标，不访问网络：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tencent_ads.py goals
```

读取当前账户的营销单元。只有用户已经配置 token 和 account_id，并且明确要求查看投放时才运行：

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tencent_ads.py adgroups-get
```

退出码 0 表示官方 JSON 的 `code` 为 0。`code` 非 0 时退出码 3，不要说投放已成功。

创建或更新必须同时有 `--body` 和 `--execute`，并且用户明确要求创建或修改这一条投放。没有 `--execute` 时退出码 2，`networkCalled` 为 false，不会创建广告。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tencent_ads.py adgroups-add --body body.json --execute
python ${OMNIMIND_PLUGIN_ROOT}/scripts/tencent_ads.py adgroups-update --body body.json --execute
```

不要运行删除。本包没有删除命令。

`oauth-token` 只在用户提供授权码或 refresh token 并要求交换时运行。不要把返回的 token 写进仓库或聊天记录。检查任务不运行这个命令。

`probe-host` 用空 token 请求正式环境，只证明主机有响应。`liveDelivery` 为 false。不要把它当成智能投放成功。
