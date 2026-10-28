---
name: onshape
description: Onshape 云端 CAD。用用户自己的 API key 创建文档、零件工作室和装配，提交特征编辑，导入文件并导出。未配置时不要启动。删除只登记显式对象，不发送删除请求。
---

# Onshape

原型行是「Onshape」，描述保持「Onshape 云端 CAD」。本目录是本地适配，不是 Onshape 或 PTC 发布的插件，也不是 lab-hardware-cad。

上游：https://github.com/onshape-public/apikey ，commit `52b6af963bc9a5c75859c93ff414914d4664941d`。MIT 正文在本包 `LICENSE`，版权人是 PTC Inc.。适配作者是 OmniMind catalog adapter。本包没有官方图标；市场行继续用原型方块图标。

## 启动

三个配置都必填，没有默认值。不要把密钥放进命令行、聊天或日志：

- `user_config.onshape_access_key` 只展开到 `ONSHAPE_ACCESS_KEY`
- `user_config.onshape_secret_key` 只展开到 `ONSHAPE_SECRET_KEY`
- `user_config.onshape_base_url` 只展开到 `ONSHAPE_BASE_URL`

示例基址是 `https://cad.onshape.com`，必须由用户显式写入。本包不创建 API key，不打开开发者门户，也不读取连接配置。缺任一配置时退出码为 2，不发请求。

只读示例需要 OAuth2Read。创建、导入和特征编辑需要相应的写权限。成功时退出码为 0。非成功状态只打印状态码，退出码为 1。缺配置时退出码为 2，不发请求。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py documents --limit 1
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py mass-by-material --document <documentId> --workspace <workspaceId> --element <elementId>
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py export-stl --document <documentId> --workspace <workspaceId> --element <elementId>
```

`documents` 对应 `Node/getDocuments.js` 的 `GET /api/documents`。允许的查询字段只有 `query`、`filter`、`owner`、`ownerType`、`sortColumn`、`sortOrder`、`offset`、`limit`。这个命令不跟随 307。

`mass-by-material` 对应 `Node/massByMaterial.js`。它先 `GET /api/parts/d/{did}/{w|v|m}/{id}/e/{eid}`，再 `GET /api/partstudios/d/{did}/{w|v|m}/{id}/e/{eid}/massproperties?massAsGroup=false`，然后只按该示例的字段汇总材料质量。必须恰好有一个版本上下文：`--workspace`、`--version` 或 `--microversion`。

`export-stl` 对应 `Node/exportStl.js` 的 `GET /api/partstudios/d/{did}/w/{wid}/e/{eid}/stl`，Accept 为 `application/vnd.onshape.v1+octet-stream`。示例用法行把 `-e` 写成了 workspaceId，代码把 `-e` 当作 elementId；本适配按代码执行。307 会重新签名，但只在配置的同一主机，或配置主机属于 `onshape.com` 时的 `https` 443 `*.onshape.com`。其他主机不跟随，访问密钥不会送出。

签名规则在 `references/signature.md`。路径和字段在 `references/operations.md`。

当前官方契约是 2026-10-15 读取的 Onshape REST API OpenAPI `1.222.90730-c8d74e607a47`，服务器 `https://cad.onshape.com/api/v17`。建模命令走 `/api/v17`。不要自己拼别的路径。

```text
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py create-document --name "Bracket"
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py create-part-studio --document <documentId> --workspace <workspaceId> --name "Studio"
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py create-assembly --document <documentId> --workspace <workspaceId> --name "Assembly"
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py get-features --document <documentId> --workspace <workspaceId> --element <elementId>
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py add-feature --document <documentId> --workspace <workspaceId> --element <elementId> --body-file feature.json
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py update-feature --document <documentId> --workspace <workspaceId> --element <elementId> --feature <featureId> --body-file feature.json
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py import-file --document <documentId> --workspace <workspaceId> --file part.step --mime application/step --format STEP
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py upload-blob --document <documentId> --workspace <workspaceId> --file note.txt --mime text/plain
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py export-translation --document <documentId> --workspace <workspaceId> --element <elementId> --format STEP
python ${OMNIMIND_PLUGIN_ROOT}/scripts/launch.py specify-delete --document <documentId> --workspace <workspaceId> --element <elementId>
```

`create-document` 对应 OpenAPI `createDocument`，也对应固定示例 `Client.new_document` 的字段 `name`、`isPublic`。未加 `--public` 时发送 `isPublic: false`。`--owner-type` 只接受示例写明的 0、1、2。

`create-part-studio` 和 `create-assembly` 对应 OpenAPI `createPartStudio`、`createAssembly`，正文只有用户给出的 `name`。零件工作室没有名字时发送 `{}`，与 Node `post` 的空正文一致。

`get-features`、`add-feature`、`update-feature` 对应 OpenAPI `getPartStudioFeatures`、`addPartStudioFeature`、`updatePartStudioFeature`。特征正文必须是用户给出的 JSON 对象，模式名是 `BTFeatureDefinitionCall-1406`，特征对象模式名是 `BTMFeature-134`。本包不编造草图或拉伸参数。先用 `get-features` 读取现有特征，再把要提交的对象写进 `--body-file`。

`import-file` 对应 OpenAPI `createTranslation`。`upload-blob` 对应固定示例 `POST /api/blobelements/d/{did}/w/{wid}`。`export-translation` 对应 OpenAPI `createPartStudioTranslation`，`formatName` 必填，没有默认格式。

`specify-delete` 只打印显式文档或元素的官方 `DELETE` 路径。它不发送请求，不删除用户资源。不要运行 `delete`、`del_document` 或 `expensiveDoNothing`。

安装本包不是已连接，也不是 CAD 已修改。没有用户自己的 API key 时，写命令是 setup_required，不是功能通过。本包不创建账号，也不产生付费。
