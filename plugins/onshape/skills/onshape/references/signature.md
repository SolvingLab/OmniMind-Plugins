# Request signature quoted from the pinned README

Source: https://github.com/onshape-public/apikey/blob/52b6af963bc9a5c75859c93ff414914d4664941d/README.md

Commit: `52b6af963bc9a5c75859c93ff414914d4664941d`

The README requires these headers:

- `Date`: UTC time of the request, accurate within 5 minutes. Example: `Mon, 11 Apr 2016 20:08:56 GMT`
- `On-Nonce`: at least 16 alphanumeric characters, unique per request. The Node sample builds 25 characters from `A-Z` and `0-9`.
- `Authorization`: `On <AccessKey>:HmacSHA256:<Signature>`

Signature input, each field separated by a newline and then lowercased:

1. HTTP method
2. On-Nonce
3. Date
4. Content-Type
5. URL pathname, with no query
6. URL query string, or an empty string when there is no query

The HMAC is SHA-256 with the secret key, then Base64. `Node/lib/onshape.js` uses `Content-Type: application/json` when the caller did not set one, and `Accept: application/vnd.onshape.v1+json` when the caller did not set one. `partStudioStl` sets `Accept: application/vnd.onshape.v1+octet-stream` and still signs `Content-Type: application/json`.

Query encoding for `GET /api/documents` follows `querystring.stringify` field order from `Node/getDocuments.js`: `query`, `filter`, `owner`, `ownerType`, `sortColumn`, `sortOrder`, `offset`, `limit`.

A 307 on `mass-by-material` and `export-stl` is re-signed for the redirect path and query. `documents` and every POST do not follow 307, so a write body is not sent to another host. Followed redirects are limited to 3 and only when the host is the configured host and port, or an `https` port 443 host under `onshape.com` when the configured origin is also under `onshape.com`. The access key is not sent to any other host. Redirect query strings are decoded and re-encoded the way Node `querystring.parse` then `querystring.stringify` does.

POST signatures use an empty query, matching `Node/lib/onshape.js` `post`. The JSON or multipart body is not part of the HMAC. Multipart `Content-Type` includes the boundary and is the signed content type. The Authorization header, access key, and secret are not printed. `specify-delete` does not sign or send a request.
