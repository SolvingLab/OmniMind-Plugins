"""Callable TikTok for Business Marketing API adapter.

Paths and parameter placement are pinned to tiktok/tiktok-business-api-sdk
commit f809c396520df2d7b201a9ccc5378d822b728ed3. This file does not vendor
that SDK and does not invent a successful ad result.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _write_stdout(text):
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()

OFFICIAL_ORIGIN = "https://business-api.tiktok.com"
SDK_COMMIT = "f809c396520df2d7b201a9ccc5378d822b728ed3"
PRODUCT = "TikTok for Business"
STABLE_ID = "proto:market:TikTok for Business"
FUNCTION = "创建、管理与分析 TikTok 广告"

# method, path, auth, and required fields copied from the SDK docs at SDK_COMMIT.
# GET non-token parameters are query parameters. access_token is the Access-Token
# header, except oauth2_access_token, which has no Access-Token header.
OPERATIONS = {
    "oauth2_access_token": {
        "method": "POST",
        "path": "/open_api/v1.3/oauth2/access_token/",
        "auth": "none",
        "body_required": ["app_id", "auth_code", "secret"],
        "doc": "https://ads.tiktok.com/marketing_api/docs?id=1739965703387137",
    },
    "oauth2_advertiser_get": {
        "method": "GET",
        "path": "/open_api/v1.3/oauth2/advertiser/get/",
        "auth": "access_token",
        "query_required": ["app_id", "secret"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1738455508553729",
    },
    "campaign_create": {
        "method": "POST",
        "path": "/open_api/v1.3/campaign/create/",
        "auth": "access_token",
        "body_required": ["advertiser_id", "campaign_name", "objective_type"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739318962329602",
    },
    "campaign_get": {
        "method": "GET",
        "path": "/open_api/v1.3/campaign/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739315828649986",
    },
    "campaign_update": {
        "method": "POST",
        "path": "/open_api/v1.3/campaign/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739320422086657",
    },
    "campaign_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/campaign/status/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739320994354178",
    },
    "adgroup_create": {
        "method": "POST",
        "path": "/open_api/v1.3/adgroup/create/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739499616346114",
    },
    "adgroup_get": {
        "method": "GET",
        "path": "/open_api/v1.3/adgroup/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739314558673922",
    },
    "adgroup_update": {
        "method": "POST",
        "path": "/open_api/v1.3/adgroup/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739586761631745",
    },
    "adgroup_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/adgroup/status/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739591716326402",
    },
    "ad_create": {
        "method": "POST",
        "path": "/open_api/v1.3/ad/create/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739953377508354",
    },
    "ad_get": {
        "method": "GET",
        "path": "/open_api/v1.3/ad/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1735735588640770",
    },
    "ad_update": {
        "method": "POST",
        "path": "/open_api/v1.3/ad/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739953405142018",
    },
    "ad_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/ad/status/update/",
        "auth": "access_token",
        "doc": "https://business-api.tiktok.com/portal/docs?id=1739953422970882",
    },
    "smart_plus_campaign_create": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/campaign/create/",
        "auth": "access_token",
    },
    "smart_plus_campaign_get": {
        "method": "GET",
        "path": "/open_api/v1.3/smart_plus/campaign/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
    },
    "smart_plus_campaign_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/campaign/update/",
        "auth": "access_token",
    },
    "smart_plus_campaign_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/campaign/status/update/",
        "auth": "access_token",
    },
    "smart_plus_adgroup_create": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/adgroup/create/",
        "auth": "access_token",
    },
    "smart_plus_adgroup_get": {
        "method": "GET",
        "path": "/open_api/v1.3/smart_plus/adgroup/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
    },
    "smart_plus_adgroup_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/adgroup/update/",
        "auth": "access_token",
    },
    "smart_plus_adgroup_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/adgroup/status/update/",
        "auth": "access_token",
    },
    "smart_plus_ad_create": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/ad/create/",
        "auth": "access_token",
    },
    "smart_plus_ad_get": {
        "method": "GET",
        "path": "/open_api/v1.3/smart_plus/ad/get/",
        "auth": "access_token",
        "query_required": ["advertiser_id"],
    },
    "smart_plus_ad_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/ad/update/",
        "auth": "access_token",
    },
    "smart_plus_ad_status_update": {
        "method": "POST",
        "path": "/open_api/v1.3/smart_plus/ad/status/update/",
        "auth": "access_token",
    },
    "report_integrated_get": {
        "method": "GET",
        "path": "/open_api/v1.3/report/integrated/get/",
        "auth": "access_token",
        "query_required": ["report_type"],
        "doc": "https://business-api.tiktok.com/portal/docs?id=1740302848100353",
    },
    "report_task_create": {
        "method": "POST",
        "path": "/open_api/v1.3/report/task/create/",
        "auth": "access_token",
    },
    "report_task_check": {
        "method": "GET",
        "path": "/open_api/v1.3/report/task/check/",
        "auth": "access_token",
        "query_required": ["task_id", "advertiser_id"],
    },
    "report_task_cancel": {
        "method": "POST",
        "path": "/open_api/v1.3/report/task/cancel/",
        "auth": "access_token",
    },
}

WRITE_OPERATIONS = {
    "oauth2_access_token",
    "campaign_create",
    "campaign_update",
    "campaign_status_update",
    "adgroup_create",
    "adgroup_update",
    "adgroup_status_update",
    "ad_create",
    "ad_update",
    "ad_status_update",
    "smart_plus_campaign_create",
    "smart_plus_campaign_update",
    "smart_plus_campaign_status_update",
    "smart_plus_adgroup_create",
    "smart_plus_adgroup_update",
    "smart_plus_adgroup_status_update",
    "smart_plus_ad_create",
    "smart_plus_ad_update",
    "smart_plus_ad_status_update",
    "report_task_create",
    "report_task_cancel",
}


def _blank(value):
    if value is None:
        return True
    return str(value).strip() == ""


def load_config(env=None):
    source = os.environ if env is None else env
    return {
        "access_token": str(source.get("TIKTOK_BUSINESS_ACCESS_TOKEN") or "").strip(),
        "app_id": str(source.get("TIKTOK_BUSINESS_APP_ID") or "").strip(),
        "app_secret": str(source.get("TIKTOK_BUSINESS_APP_SECRET") or "").strip(),
        "advertiser_id": str(source.get("TIKTOK_BUSINESS_ADVERTISER_ID") or "").strip(),
        "api_base": str(source.get("TIKTOK_BUSINESS_API_BASE") or OFFICIAL_ORIGIN).strip(),
        "allow_unofficial_base": str(source.get("TIKTOK_BUSINESS_ALLOW_UNOFFICIAL_BASE") or "").strip() == "1",
    }


def configured_flags(config):
    return {
        "access_token": not _blank(config["access_token"]),
        "app_id": not _blank(config["app_id"]),
        "app_secret": not _blank(config["app_secret"]),
        "advertiser_id": not _blank(config["advertiser_id"]),
    }


def secrets_from(config, query=None, body=None):
    found = []
    for key in ("access_token", "app_secret"):
        if config.get(key):
            found.append(config[key])
    for payload in (query or {}, body or {}):
        if not isinstance(payload, dict):
            continue
        for key in ("secret", "auth_code", "access_token", "app_secret"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                found.append(value.strip())
    return [item for item in found if item]


def redact_text(text, secrets):
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def status_payload(env=None):
    config = load_config(env)
    flags = configured_flags(config)
    unavailable = None if flags["access_token"] else "credentials_missing"
    return {
        "product": PRODUCT,
        "stableId": STABLE_ID,
        "function": FUNCTION,
        "configured": flags,
        "unavailable": unavailable,
        "apiBase": OFFICIAL_ORIGIN,
        "configuredBaseIsOfficial": config["api_base"].rstrip("/") == OFFICIAL_ORIGIN,
        "liveCall": False,
        "accountConnected": False,
        "sdkCommit": SDK_COMMIT,
        "operations": sorted(OPERATIONS),
    }


def _encode_query_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _origin_ok(config):
    base = config["api_base"].rstrip("/")
    if base == OFFICIAL_ORIGIN:
        return True
    return config["allow_unofficial_base"] and base.startswith("https://")


def build_call(operation, query=None, body=None, env=None):
    spec = OPERATIONS.get(operation)
    if spec is None:
        return {
            "ok": False,
            "unavailable": "unknown_operation",
            "operation": operation,
            "liveCall": False,
            "error": "Unknown TikTok for Business operation",
        }
    config = load_config(env)
    if not _origin_ok(config):
        return {
            "ok": False,
            "unavailable": "unofficial_base_rejected",
            "operation": operation,
            "liveCall": False,
            "error": "API base must be https://business-api.tiktok.com",
        }
    query_out = dict(query or {})
    body_out = dict(body or {})
    if spec["method"] == "GET" and body:
        return {
            "ok": False,
            "unavailable": "body_not_allowed",
            "operation": operation,
            "liveCall": False,
            "error": "GET operations take query parameters, not a JSON body",
        }
    if spec["method"] == "POST" and query:
        return {
            "ok": False,
            "unavailable": "query_not_allowed",
            "operation": operation,
            "liveCall": False,
            "error": "POST operations take a JSON body. Access-Token is a header, not a query parameter",
        }
    if "advertiser_id" in spec.get("query_required", []) and _blank(query_out.get("advertiser_id")):
        if config["advertiser_id"]:
            query_out["advertiser_id"] = config["advertiser_id"]
    if "advertiser_id" in spec.get("body_required", []) and _blank(body_out.get("advertiser_id")):
        if config["advertiser_id"]:
            body_out["advertiser_id"] = config["advertiser_id"]
    if operation == "oauth2_access_token":
        if _blank(body_out.get("app_id")) and config["app_id"]:
            body_out["app_id"] = config["app_id"]
        if _blank(body_out.get("secret")) and config["app_secret"]:
            body_out["secret"] = config["app_secret"]
    if operation == "oauth2_advertiser_get":
        if _blank(query_out.get("app_id")) and config["app_id"]:
            query_out["app_id"] = config["app_id"]
        if _blank(query_out.get("secret")) and config["app_secret"]:
            query_out["secret"] = config["app_secret"]
    missing = []
    if spec["auth"] == "access_token" and _blank(config["access_token"]):
        missing.append("access_token")
    for key in spec.get("query_required", []):
        if _blank(query_out.get(key)):
            missing.append(key)
    for key in spec.get("body_required", []):
        if _blank(body_out.get(key)):
            missing.append(key)
    if spec["method"] == "POST" and not spec.get("body_required") and not body_out:
        missing.append("body")
    if missing:
        return {
            "ok": False,
            "unavailable": "credentials_missing" if missing == ["access_token"] else "required_fields_missing",
            "operation": operation,
            "missing": missing,
            "liveCall": False,
            "error": "TikTok for Business is not configured for this operation",
        }
    headers = {"Accept": "application/json"}
    if spec["auth"] == "access_token":
        headers["Access-Token"] = config["access_token"]
    url = config["api_base"].rstrip("/") + spec["path"]
    data = None
    if spec["method"] == "GET":
        encoded = urllib.parse.urlencode(
            [(key, _encode_query_value(value)) for key, value in query_out.items() if not _blank(value)]
        )
        if encoded:
            url = url + "?" + encoded
    else:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body_out, ensure_ascii=False).encode("utf-8")
    return {
        "ok": True,
        "operation": operation,
        "liveCall": False,
        "request": {
            "method": spec["method"],
            "url": url,
            "headers": headers,
            "data": data,
        },
        "secrets": secrets_from(config, query_out, body_out),
    }


def _response_ok(status, payload):
    if isinstance(payload, dict) and "code" in payload and payload["code"] is not None:
        return str(payload["code"]) == "0"
    return 200 <= status < 300


def execute_prepared(prepared, opener=None):
    if not prepared.get("ok"):
        return prepared
    request = prepared["request"]
    secrets = prepared.get("secrets") or []
    open_url = opener or urllib.request.urlopen
    http_request = urllib.request.Request(
        request["url"],
        data=request["data"],
        headers=request["headers"],
        method=request["method"],
    )
    try:
        with open_url(http_request, timeout=30) as response:
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "operation": prepared["operation"],
            "liveCall": True,
            "transportError": True,
            "error": redact_text(str(exc.reason), secrets),
        }
    text = raw.decode("utf-8", "replace")
    try:
        payload = json.loads(text) if text else None
    except json.JSONDecodeError:
        payload = None
    ok = _response_ok(status, payload)
    result = {
        "ok": ok,
        "operation": prepared["operation"],
        "liveCall": True,
        "httpStatus": status,
        "response": payload if payload is not None else redact_text(text[:2000], secrets),
    }
    if not ok:
        message = payload.get("message") if isinstance(payload, dict) else text[:500]
        result["error"] = redact_text(str(message), secrets)
        if isinstance(payload, dict) and "code" in payload:
            result["apiCode"] = payload.get("code")
    return result


def call_operation(operation, query=None, body=None, env=None, opener=None):
    prepared = build_call(operation, query=query, body=body, env=env)
    if not prepared.get("ok"):
        return prepared
    return execute_prepared(prepared, opener=opener)


def prepare_view(prepared):
    if not prepared.get("ok"):
        return prepared
    request = prepared["request"]
    parsed = urllib.parse.urlsplit(request["url"])
    query_keys = [key for key, _value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)]
    body_keys = []
    if request["data"]:
        body_keys = sorted(json.loads(request["data"].decode("utf-8")).keys())
    return {
        "ok": True,
        "operation": prepared["operation"],
        "liveCall": False,
        "method": request["method"],
        "path": parsed.path,
        "host": parsed.hostname,
        "queryKeys": query_keys,
        "bodyKeys": body_keys,
        "hasAccessTokenHeader": "Access-Token" in request["headers"],
    }


def _read_json_arg(text):
    if text.startswith("@"):
        with open(text[1:], encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("JSON argument must be an object")
    return value


def _emit(payload):
    _write_stdout(json.dumps(payload, ensure_ascii=False) + "\n")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        _emit(
            {
                "ok": False,
                "unavailable": "usage",
                "commands": ["status", "operations", "prepare <operation>", "call <operation>", "mcp"],
            }
        )
        return 2
    command = args[0]
    if command == "status":
        payload = status_payload()
        _emit(payload)
        return 0 if payload["configured"]["access_token"] else 2
    if command == "operations":
        _emit(
            {
                "ok": True,
                "liveCall": False,
                "operations": [
                    {
                        "name": name,
                        "method": spec["method"],
                        "path": spec["path"],
                        "write": name in WRITE_OPERATIONS,
                        "doc": spec.get("doc"),
                    }
                    for name, spec in OPERATIONS.items()
                ],
            }
        )
        return 0
    if command == "mcp":
        return serve_mcp()
    if command in ("prepare", "call"):
        if len(args) < 2:
            _emit({"ok": False, "unavailable": "usage", "error": "operation is required"})
            return 2
        operation = args[1]
        query = None
        body = None
        index = 2
        while index < len(args):
            flag = args[index]
            if flag not in ("--query", "--body") or index + 1 >= len(args):
                _emit({"ok": False, "unavailable": "usage", "error": "expected --query or --body"})
                return 2
            try:
                parsed = _read_json_arg(args[index + 1])
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                _emit({"ok": False, "unavailable": "invalid_json", "error": str(exc)})
                return 2
            if flag == "--query":
                query = parsed
            else:
                body = parsed
            index += 2
        prepared = build_call(operation, query=query, body=body)
        if command == "prepare":
            view = prepare_view(prepared)
            _emit(view)
            return 0 if view.get("ok") else 2
        result = execute_prepared(prepared) if prepared.get("ok") else prepared
        _emit(result)
        if result.get("ok"):
            return 0
        if result.get("unavailable"):
            return 2
        return 1
    _emit({"ok": False, "unavailable": "usage", "error": "unknown command"})
    return 2


def _mcp_tools():
    return [
        {
            "name": "tiktok_business_status",
            "description": "Report whether TikTok for Business credentials are configured. Does not call the API or reveal secrets.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "tiktok_business_call",
            "description": "Call one pinned TikTok Marketing API operation to create, manage, or analyze ads. Writes require explicit user confirmation. Missing credentials return unavailable and do not invent a result.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "query": {"type": "object"},
                    "body": {"type": "object"},
                },
                "required": ["operation"],
                "additionalProperties": False,
            },
        },
    ]


def _mcp_write(payload):
    _write_stdout(json.dumps(payload, ensure_ascii=False) + "\n")


def serve_mcp(stdin=None, stdout_write=None):
    reader = sys.stdin if stdin is None else stdin
    write = _mcp_write if stdout_write is None else stdout_write
    for line in reader:
        text = line.strip()
        if not text:
            continue
        try:
            request = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(request, dict) or "id" not in request:
            continue
        method = request.get("method")
        if method == "initialize":
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            result = {
                "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tiktok-for-business", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": _mcp_tools()}
        elif method == "ping":
            result = {}
        elif method == "tools/call":
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            name = params.get("name")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if name == "tiktok_business_status":
                payload = status_payload()
                is_error = payload["unavailable"] is not None
            elif name == "tiktok_business_call":
                payload = call_operation(
                    arguments.get("operation"),
                    query=arguments.get("query"),
                    body=arguments.get("body"),
                )
                is_error = not payload.get("ok")
            else:
                write(
                    {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "error": {"code": -32602, "message": "Unknown tool"},
                    }
                )
                continue
            result = {
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                "isError": is_error,
            }
        else:
            write(
                {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                }
            )
            continue
        write({"jsonrpc": "2.0", "id": request["id"], "result": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
