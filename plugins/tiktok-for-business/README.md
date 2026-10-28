# TikTok for Business

Prototype `proto:market:TikTok for Business`. Function: 创建、管理与分析 TikTok 广告.

This package is a stdlib Python adapter over the official TikTok Marketing API. It is not the TikTok Business API SDK, and it does not ship a simulated ads account.

Callable entrypoint: `scripts/tiktok_business.py`

- `status` reports whether an access token is configured. It does not call the network.
- `prepare <operation>` prints the pinned method and path with secrets removed.
- `call <operation>` sends the request to `https://business-api.tiktok.com` when required credentials and fields are present.
- `mcp` speaks newline-delimited JSON-RPC tools `tiktok_business_status` and `tiktok_business_call`.

Missing credentials return `unavailable` and exit 2. They do not create a campaign or a report.

The operation table is pinned to `tiktok/tiktok-business-api-sdk` commit `f809c396520df2d7b201a9ccc5378d822b728ed3`. See `SOURCE.json` and `skills/tiktok-for-business/references/marketing-api.md`.

What local checks cover: request construction, credential refusal, secret redaction, and the MCP handshake. What they do not cover: a TikTok advertiser account, a live campaign create, or a live report. Native acceptance remains with Main.
