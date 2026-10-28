# Operations quoted from the pinned Node sample

Source commit: `52b6af963bc9a5c75859c93ff414914d4664941d`

## documents

`Node/lib/app.js` `getDocuments` sends:

```text
GET /api/documents
```

`Node/getDocuments.js` and `Node/README.md` name these query fields:

```text
query filter owner ownerType sortColumn sortOrder offset limit
```

Usage line from that README:

```text
node getDocuments.js [--query <query>] [--filter <filter>] [--owner <owner>] [--ownerType <ownerType>] [--sortColumn <sortColumn>] [--sortOrder <sortOrder>] [--offset <offset>] [--limit <limit>]
```

The sample says this requires OAuth2Read. It does not define the allowed values of those fields beyond "See API documentation for query parameters." This adapter accepts only those field names and does not invent values.

## mass-by-material

`Node/README.md` usage:

```text
node massByMaterial.js -d <documentId> -[wvm] <wvmId> -e <elementId>
```

`Node/lib/app.js` builds the two reads used by `Node/massByMaterial.js`:

```text
GET /api/parts/d/{documentId}/{w|v|m}/{wvmId}/e/{elementId}
GET /api/partstudios/d/{documentId}/{w|v|m}/{wvmId}/e/{elementId}/massproperties?massAsGroup=false
```

The sample keeps parts whose `material` is present, groups `partId` by `material.id`, and adds `bodies[partId].mass[0]` only when `hasMass` is true. This adapter prints that tally as JSON. It does not add fields the sample does not read.

## export-stl

`Node/README.md` usage, including its element-id label:

```text
node exportStl.js -d <documentId> -w <workspaceId> -e <workspaceId>
```

`Node/exportStl.js` passes `-d`, `-w`, and `-e` to `partStudioStl` as document, workspace, and element. `Node/lib/app.js` sends:

```text
GET /api/partstudios/d/{documentId}/w/{workspaceId}/e/{elementId}/stl
Accept: application/vnd.onshape.v1+octet-stream
```

The query object in that call is null. This adapter does not add STL query fields.

## Current modeling contract

Fetched from `https://cad.onshape.com/api/openapi` on 2026-10-15. `info.version` is `1.222.90730-c8d74e607a47`. `servers[0].url` is `https://cad.onshape.com/api/v17`. Paths below are that server prefix plus the OpenAPI path. The user origin replaces `https://cad.onshape.com`; the version prefix stays `/api/v17`.

```text
POST /api/v17/documents
POST /api/v17/partstudios/d/{documentId}/w/{workspaceId}
POST /api/v17/assemblies/d/{documentId}/w/{workspaceId}
GET  /api/v17/partstudios/d/{documentId}/w/{workspaceId}/e/{elementId}/features
POST /api/v17/partstudios/d/{documentId}/w/{workspaceId}/e/{elementId}/features
POST /api/v17/partstudios/d/{documentId}/w/{workspaceId}/e/{elementId}/features/featureid/{featureId}
POST /api/v17/translations/d/{documentId}/w/{workspaceId}
POST /api/v17/partstudios/d/{documentId}/w/{workspaceId}/e/{elementId}/translations
```

`createDocument` body fields used here are `name`, `isPublic`, and `ownerType` only when the caller passes 0, 1, or 2. `createPartStudio` and `createAssembly` send `name` only when given. `addPartStudioFeature` and `updatePartStudioFeature` post the caller JSON object unchanged. The OpenAPI schema names are `BTFeatureDefinitionCall-1406` and `BTMFeature-134`. `createPartStudioTranslation` requires `formatName`. `createTranslation` is multipart, with `encodedFilename`, optional `formatName`, and `file`.

The pinned sample upload remains a separate command:

```text
POST /api/blobelements/d/{documentId}/w/{workspaceId}
```

Its multipart fields are `encodedFilename`, `fileContentLength`, and `file`, as in `Node/lib/onshape.js` `upload` and `python/apikey/client.py` `upload_blob`.

## Delete is specification only

OpenAPI `deleteElement` is `DELETE /api/v17/elements/d/{documentId}/w/{workspaceId}/e/{elementId}`. OpenAPI `deleteDocument` is `DELETE /api/v17/documents/{documentId}`. `specify-delete` prints one of those paths for an explicit id and does not send it. `forever` is not accepted. `expensiveDoNothing` is not a command because it deletes the element it just created.
