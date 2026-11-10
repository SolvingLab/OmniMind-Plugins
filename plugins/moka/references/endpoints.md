# Moka HR workflow endpoints

Pinned 2026-10-15 from the official docs. This file records the callable contract. It is not a copy of the docs.

China production origin: `https://api.mokahr.com`. Staging: `https://api-staging-3.mokahr.com`. International: `https://hire-r1-api.mokahr.com`.

## ATS recruitment workflow

Source: https://www.mokahr.com/docs/api/

Auth: `Authorization: Basic base64(apiKey + ":")`. The docs' curl is `-u 'your_api_key:'`.

- `GET /api-platform/v2/pipelines/getPipelinesList` — 获取招聘流程列表. No documented query.
- `GET /api-platform/v1/pipelines/list?currentHireMode=1|2` — 获取招聘流程列表. `1` social, `2` campus. Required.
- `GET /api-platform/v2/stage/getStagesList` — 获取阶段信息列表. No documented query.

These are two different pipeline contracts. The adapter does not merge them.

## People approval workflow

Source: https://people.mokahr.com/docs/api/view/v1.html

`POST /api-platform/hcm/oapi/v2/workflow/flowInstance/form-data`

Query: `entCode`, `apiCode`, `nonce`, `timestamp`, `sign`.

`apiCode` is the interface code from Moka People 设置 - 对外接口设置, data source 审批表单详情查询. `entCode` comes from the CSM. `nonce` is at most 8 letters or digits. `timestamp` is milliseconds. The same page says the timestamp must be within 3 minutes and a nonce must not repeat within 5 minutes.

Body: `{"flowInstanceId":"<positive integer, at most 19 digits>"}`.

Sign: sort every query field except `sign`, join `key=value` with `&`, MD5withRSA over that UTF-8 string using the tenant PKCS#8 private key, then URL-encode `sign`.

Header: the same Basic auth. The People page says `Basic Base64.encode(apiKey:)` and the colon must not be omitted.

Documented rate limit for this call: 10 times per second per company, 300 times per minute per company. This adapter sends one request per invocation.

## Writes

These mutate a tenant. The adapter sends them only when that command is invoked and the required config is present. Missing config exits 2 and does not send. This package does not call them during its own checks.

Source for the ATS writes: https://www.mokahr.com/docs/api/

- `PUT /api-platform/v1/applications/move_application_stage?applicationId={id}&stageId={id}` — 将申请移动到所在职位下的任一阶段. Both ids are required. The sample curl uses `http`, but the documented HTTP request line and the global rule are HTTPS.
- `POST /api-platform/v1/create-offer` — 创建Offer. Body requires `applicationId`. Optional documented fields may be supplied in `--body-file`. CSM must enable the feature.
- `PUT /api-platform/v1/applications/offerApproval` — 审批offer. Body requires `applicationId` and `status`: `1` approve, `2` reject, `3` in progress. CSM must enable external approval.
- `POST /api-platform/v1/sendOffer` — 发送offer. Body requires `applicationId` and `hrEmail`.
- `PUT /api-platform/v1/offer/status` — 接收/拒绝Offer. Query requires `applicationId` and `accepted` (`1` or `0`). `reasonId` is required when `accepted` is `0`.
- `PUT /api-platform/v1/applications/{applicationId}/hired` — 标记候选人已入职. Body requires `hiredAt` and `probation` (`0` through `6`).

Source for the People writes: https://people.mokahr.com/docs/api/view/v1.html

- `POST /api-platform/hcm/oapi/v2/core/rosters/batchAddJobChange` — 新增员工异动数据接口. Query adds required `userName` to the signed People query. `apiCode` data source is 新增异动记录接口. Body `data` is 1 to 200 items. Each item requires `employee_uid`, `effect_date`, and `event_type`.
- `POST /api-platform/hcm/oapi/v1/basic/ob/employee/batchCreate` — 批量添加待入职员工. `apiCode` data source is 批量新增待入职员工. Body `data` is 1 to 100 items. Each item requires `realName`, `onBoardingPlan`, `department` (`departmentId` or `departmentNo`), `employeeTypeId`, `onBoardingDate`, `telephoneCountryCode`, `telephone`, `personalEmail`, `idNoIdType`, and `idNo`.

Do not reuse the approval-form `apiCode` for these data sources.

## Not called

Offer field update, offer template list, resignation, correction-to-regular, absence, salary, and webhooks stay outside this slice.
