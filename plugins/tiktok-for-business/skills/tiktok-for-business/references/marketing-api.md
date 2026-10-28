# TikTok Marketing API pin

Contract commit: `f809c396520df2d7b201a9ccc5378d822b728ed3` in `tiktok/tiktok-business-api-sdk`.

Origin: `https://business-api.tiktok.com`

Authorized calls send `Access-Token` as a header. `oauth2_access_token` does not. That placement is from `python_sdk/business_api_client/api/campaign_creation_api.py` and `authentication_api.py` at this commit.

GET list and object query values are JSON-encoded because `yml_files/report_integrated_get.yml` declares those query parameters with `content: application/json`.

Response envelope fields `code`, `message`, `data`, and `request_id` are from that same report spec. A present `code` other than `0` is an API error. This package has not observed a live successful ad write.

| Operation | Method | Path | Doc |
| --- | --- | --- | --- |
| oauth2_access_token | POST | /open_api/v1.3/oauth2/access_token/ | https://ads.tiktok.com/marketing_api/docs?id=1739965703387137 |
| oauth2_advertiser_get | GET | /open_api/v1.3/oauth2/advertiser/get/ | https://business-api.tiktok.com/portal/docs?id=1738455508553729 |
| campaign_create | POST | /open_api/v1.3/campaign/create/ | https://business-api.tiktok.com/portal/docs?id=1739318962329602 |
| campaign_get | GET | /open_api/v1.3/campaign/get/ | https://business-api.tiktok.com/portal/docs?id=1739315828649986 |
| campaign_update | POST | /open_api/v1.3/campaign/update/ | https://business-api.tiktok.com/portal/docs?id=1739320422086657 |
| campaign_status_update | POST | /open_api/v1.3/campaign/status/update/ | https://business-api.tiktok.com/portal/docs?id=1739320994354178 |
| adgroup_create | POST | /open_api/v1.3/adgroup/create/ | https://business-api.tiktok.com/portal/docs?id=1739499616346114 |
| adgroup_get | GET | /open_api/v1.3/adgroup/get/ | https://business-api.tiktok.com/portal/docs?id=1739314558673922 |
| adgroup_update | POST | /open_api/v1.3/adgroup/update/ | https://business-api.tiktok.com/portal/docs?id=1739586761631745 |
| adgroup_status_update | POST | /open_api/v1.3/adgroup/status/update/ | https://business-api.tiktok.com/portal/docs?id=1739591716326402 |
| ad_create | POST | /open_api/v1.3/ad/create/ | https://business-api.tiktok.com/portal/docs?id=1739953377508354 |
| ad_get | GET | /open_api/v1.3/ad/get/ | https://business-api.tiktok.com/portal/docs?id=1735735588640770 |
| ad_update | POST | /open_api/v1.3/ad/update/ | https://business-api.tiktok.com/portal/docs?id=1739953405142018 |
| ad_status_update | POST | /open_api/v1.3/ad/status/update/ | https://business-api.tiktok.com/portal/docs?id=1739953422970882 |
| smart_plus_campaign_create | POST | /open_api/v1.3/smart_plus/campaign/create/ | SDK method table at this commit |
| smart_plus_campaign_get | GET | /open_api/v1.3/smart_plus/campaign/get/ | SDK method table at this commit |
| smart_plus_campaign_update | POST | /open_api/v1.3/smart_plus/campaign/update/ | SDK method table at this commit |
| smart_plus_campaign_status_update | POST | /open_api/v1.3/smart_plus/campaign/status/update/ | SDK method table at this commit |
| smart_plus_adgroup_create | POST | /open_api/v1.3/smart_plus/adgroup/create/ | SDK method table at this commit |
| smart_plus_adgroup_get | GET | /open_api/v1.3/smart_plus/adgroup/get/ | SDK method table at this commit |
| smart_plus_adgroup_update | POST | /open_api/v1.3/smart_plus/adgroup/update/ | SDK method table at this commit |
| smart_plus_adgroup_status_update | POST | /open_api/v1.3/smart_plus/adgroup/status/update/ | SDK method table at this commit |
| smart_plus_ad_create | POST | /open_api/v1.3/smart_plus/ad/create/ | SDK method table at this commit |
| smart_plus_ad_get | GET | /open_api/v1.3/smart_plus/ad/get/ | SDK method table at this commit |
| smart_plus_ad_update | POST | /open_api/v1.3/smart_plus/ad/update/ | SDK method table at this commit |
| smart_plus_ad_status_update | POST | /open_api/v1.3/smart_plus/ad/status/update/ | SDK method table at this commit |
| report_integrated_get | GET | /open_api/v1.3/report/integrated/get/ | https://business-api.tiktok.com/portal/docs?id=1740302848100353 |
| report_task_create | POST | /open_api/v1.3/report/task/create/ | SDK ReportingApi.md at this commit |
| report_task_check | GET | /open_api/v1.3/report/task/check/ | SDK ReportingApi.md at this commit |
| report_task_cancel | POST | /open_api/v1.3/report/task/cancel/ | SDK ReportingApi.md at this commit |

`campaign_create` body required fields pinned from `CampaignCreateBody.md`: `advertiser_id`, `campaign_name`, `objective_type`.

`oauth2_access_token` body required fields pinned from `Oauth2AccessTokenBody.md`: `app_id`, `auth_code`, `secret`.

`oauth2_advertiser_get` sends `app_id` and `secret` as query parameters and `Access-Token` as a header, matching `authentication_api.py`.

Authentication overview: https://ads.tiktok.com/marketing_api/docs?id=1738373164380162

Return codes appendix: https://ads.tiktok.com/marketing_api/docs?id=1737172488964097
