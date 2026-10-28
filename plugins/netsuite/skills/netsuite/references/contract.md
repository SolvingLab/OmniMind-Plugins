# SuiteTalk connect contract

This adapter calls only the two official requests below. It is not an Oracle client and it does not implement TBA, the authorization-code browser flow, SuiteQL, or record writes.

Pages were fetched on 2026-10-15 from `docs.oracle.com`. Hashes are in `SOURCE.json`.

## Authentication

Oracle's REST guide says OAuth 2.0 is preferred, and that new TBA integrations stop being creatable in 2027.1. This package therefore uses the client-credentials flow only.

- Flow: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162730264820.html
- Token request: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162755359851.html
- JWT claims: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162790605110.html
- Bearer header: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_157780312610.html

Token URL, with the Company URLs host:

```text
POST https://<host>/services/rest/auth/oauth2/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion=<jwt>
```

JWT header is `typ=JWT`, `alg` from configuration, `kid` = certificate ID. Payload is `iss` = client ID, `scope` = `["rest_webservices"]`, `aud` = that same token URL, `jti`, `iat`, and `exp = iat + 300`. The parameter table says `exp` must be less than 60 minutes greater than `iat`. The sample assertion on the token page uses 3600 seconds and also includes `jti`, which the parameter table does not list. This adapter includes `jti` and uses 300 seconds.

The sample assertion's `scope` is a JSON array. The parameter table says the scope values are separated by a comma. This adapter follows the sample array and sends only `rest_webservices`.

The sample assertion's `aud` uses `restlets.api.netsuite.com`. The same token page says the token endpoint and `aud` use `<accountID>.suitetalk.api.netsuite.com`. This adapter sets `aud` to the SuiteTalk token URL it posts to. It does not post to `restlets.api.netsuite.com`.

Supported `alg` values are PS256, PS384, PS512, ES256, ES384, and ES512. RSA algorithms use RSASSA-PSS with a salt length equal to the digest. EC algorithms use IEEE-P1363 signatures. A key that does not match `alg` produces no request.

## Host

- URL schema: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1546938065.html
- Account-specific domains: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1498251763.html

The service URL is a required configuration value from Company Information > Company URLs. The adapter does not invent a host. It sends the private key only when that origin is `https` port 443, has no user, path, or query, and the host equals the documented transform of the account ID: underscores become hyphens and letters become lowercase, then `.suitetalk.api.netsuite.com`. Documented examples: `123456` → `123456.suitetalk.api.netsuite.com`; `123456_SB1` → `123456-sb1.suitetalk.api.netsuite.com`; `123456_RP` → `123456-rp.suitetalk.api.netsuite.com`.

A mismatch, including a `restlets.api.netsuite.com` host, exits 2 and sends nothing.

## Connect read

- Metadata: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1540810174.html

After a bearer token is returned, one GET is sent:

```text
GET https://<host>/services/rest/record/v1/metadata-catalog
Authorization: Bearer <access token>
Accept: application/json
```

The metadata topic's example uses `http://`. The URL schema examples use `https://`. This adapter sends `https` only. No `select` query is added. The documented response shape is an object with an `items` array. A 200 without `items` is not connected.

Redirects are not followed. The access token and private key are not printed. HTTP statuses other than 200 are not treated as connected. Record create, update, delete, and SuiteQL are not implemented.
