# 腾讯广告

原型「腾讯广告」的智能投放适配。调用腾讯广告 Marketing API v3.0，不下载 Go SDK，不创建开发者应用，不代填 token。

上游：https://github.com/TencentAd/marketing-api-go-sdk 标签 `v1.7.87`，commit `81d6cc04b58d7d5a5ec9ad0137e43b3b6c52fde9`。Apache-2.0 正文见 `LICENSE`。

未配置 `TENCENT_ADS_ACCESS_TOKEN` 或 `TENCENT_ADS_ACCOUNT_ID` 时，`scripts/tencent_ads.py status` 退出码为 2，不请求账户。

图标是 developers.e.qq.com、e.qq.com、ad.qq.com 返回的同一份 PNG 字节，来源说明见 `assets/icon-NOTICE.md`。不是自绘替代标志。
