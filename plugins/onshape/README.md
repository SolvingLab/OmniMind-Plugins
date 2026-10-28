# Onshape

原型「Onshape」的本地适配，描述保持「Onshape 云端 CAD」。只读调用来自已固定 API key 示例。文档、零件工作室、装配、特征编辑、导入和格式导出使用 Onshape REST API OpenAPI `1.222.90730-c8d74e607a47` 的 `/api/v17`。删除只登记显式对象，不发送删除。不创建 API key，也不使用 Onshape 标志。

上游：https://github.com/onshape-public/apikey commit `52b6af963bc9a5c75859c93ff414914d4664941d`。MIT 正文见 `LICENSE`。适配作者不是 PTC。

入口是 `scripts/launch.py`。未配置 `ONSHAPE_ACCESS_KEY`、`ONSHAPE_SECRET_KEY`、`ONSHAPE_BASE_URL` 时退出码为 2，不发请求。协议检查使用本机夹具和合成密钥，不是 Onshape 在线通过。
