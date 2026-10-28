# 百度网盘

Callable adapter for prototype `proto:market:百度网盘`, function 云端文件与资料管理.

The entrypoint is `scripts/netdisk.py`. Without `BAIDU_NETDISK_ACCESS_TOKEN` it exits 2 and does not call the file API. The official MCP SSE address is declared in `.omnimind-plugin/plugin.json` and stays disabled until the user supplies a token.

This package is not Google Drive, WPS cloud docs, or an unofficial PCS client. Provenance is in `SOURCE.json`.
