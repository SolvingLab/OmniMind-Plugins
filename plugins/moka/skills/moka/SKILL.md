---
name: moka
description: 读取 Moka HR 工作流。未配置 MOKA_API_KEY 时不请求。不把其它 HR 产品当作 Moka，也不代用户审批或写入人事数据。
---

# Moka HR 工作流

原型名称是 Moka，描述是「Moka HR 工作流」。本包只调用 Moka 官方 OpenAPI。它不是泛用 HR 工具，不是其它招聘系统，也不是 Kimi 原包。

开放平台：https://open.mokahr.com/ 。ATS 文档：https://www.mokahr.com/docs/api/ 。People 文档：https://people.mokahr.com/docs/api/view/v1.html 。合同摘录在 `references/endpoints.md`。

## 配置

把 `user_config` 只放进对应环境变量，不要打印值，不要写入仓库：

- `user_config.api_key` → `MOKA_API_KEY`
- `user_config.api_host` → `MOKA_API_HOST`（可空。空则使用文档中的中国正式域名 `https://api.mokahr.com`）
- `user_config.ent_code` → `MOKA_ENT_CODE`
- `user_config.api_code` → `MOKA_API_CODE`
- `user_config.private_key` → `MOKA_PRIVATE_KEY`
- `user_config.user_name` → `MOKA_USER_NAME`（仅人事异动）
- `user_config.job_change_api_code` → `MOKA_JOB_CHANGE_API_CODE`
- `user_config.onboarding_api_code` → `MOKA_ONBOARDING_API_CODE`

私钥也可以只放在 `MOKA_PRIVATE_KEY_FILE` 的绝对路径。不要同时设置两者。不要读取用户主目录来猜测密钥。审批表单、异动、待入职各自有自己的 apiCode，不要混用。

没有 API Key 时，命令退出码为 2，状态是 `setup_required`，不会发请求。这不是工作流读取成功。

## 命令

在插件根目录运行：

```text
node scripts/moka_hr_workflow.mjs status
node scripts/moka_hr_workflow.mjs ats-pipelines
node scripts/moka_hr_workflow.mjs ats-pipelines-v1 --hire-mode 1
node scripts/moka_hr_workflow.mjs ats-stages
node scripts/moka_hr_workflow.mjs people-approval-form --flow-instance-id 619481843815727104
```

`ats-pipelines` 和 `ats-stages` 读取招聘流程和阶段。`ats-pipelines-v1` 是文档里的另一条招聘流程列表，必须带 `--hire-mode 1` 或 `2`。`people-approval-form` 读取一条 People 审批单的表单。示例 id 来自官方文档，不是本机数据。没有用户给出的真实实例 id 时不要调用。

这些读取命令在配置齐全时会连接用户自己的 Moka 租户。只有用户明确要求读取该工作流时才运行。不要循环调用。People 审批表单接口文档限制为每企业每秒 10 次、每分钟 300 次。

## 写入

写入会改变租户数据。只有用户明确要求这一步时才运行。检查和验收准备不得代跑这些命令。没有真实账号时不要发明 id、邮箱或私钥。

```text
node scripts/moka_hr_workflow.mjs ats-move-stage --application-id 96 --stage-id 4
node scripts/moka_hr_workflow.mjs ats-create-offer --application-id 12
node scripts/moka_hr_workflow.mjs ats-approve-offer --application-id 12 --status 1
node scripts/moka_hr_workflow.mjs ats-send-offer --application-id 1234 --hr-email hr@example.com
node scripts/moka_hr_workflow.mjs ats-offer-feedback --application-id 89 --accepted 0 --reason-id 1
node scripts/moka_hr_workflow.mjs ats-mark-hired --application-id 33582 --hired-at 2018-08-06T16:00:00.000Z --probation 3
node scripts/moka_hr_workflow.mjs people-add-job-change --body-file C:\absolute\job-change.json
node scripts/moka_hr_workflow.mjs people-create-onboarding --body-file C:\absolute\onboarding.json
```

上面的数字和邮箱是官方文档样例，不是本机数据。`--status` 只接受 `1` 通过、`2` 驳回、`3` 审批中。拒绝 Offer 时必须有 `--reason-id`。人事异动还要 `MOKA_USER_NAME`。异动和待入职的 apiCode 分别对应数据源「新增异动记录接口」和「批量新增待入职员工」。

`sign-self-check` 只用临时密钥验证本地 MD5withRSA，不访问 Moka。`probe-auth-required` 对招聘流程地址发一次不带凭证的 GET，用来确认入口要求鉴权。它不是功能通过。

## 不做的事

不要写假勤、薪酬、离职或转正。文档里有这些接口，本包没有实现。不要编造 API Key、entCode、apiCode 或私钥。不要把退出码 0 的本地自检或模拟请求说成已写入租户。真实账号验收仍由 Main 做。
