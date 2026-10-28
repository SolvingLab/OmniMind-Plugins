"""Call Tencent Ads Marketing API v3 smart-delivery endpoints.

Interface pins are in references/pinned-interface.json. This file does not
bundle the Go SDK and does not invent credentials, accounts, or ad groups.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = PACKAGE_ROOT / "references" / "pinned-interface.json"
GOALS_PATH = PACKAGE_ROOT / "references" / "smart-delivery-goals.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pin():
    return load_json(PIN_PATH)


def goals():
    return load_json(GOALS_PATH)


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return code


def env_value(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def nonce_from_uuid(value: str) -> str:
    # Same slice as pkg/ads/v3/middleware_auth.go at the pinned commit.
    return value[0:8] + value[9:13] + value[14:18]


def new_nonce() -> str:
    return nonce_from_uuid(str(uuid.uuid4()))


def allowed_base(value: str, facts: dict) -> str:
    normalized = value.rstrip("/")
    allowed = {item.rstrip("/") for item in facts["adgroupsBases"]}
    if normalized not in allowed:
        raise ValueError(
            "setup_required: TENCENT_ADS_API_BASE must be one of "
            + ", ".join(facts["adgroupsBases"])
        )
    return normalized


def account_id_value(raw: str) -> str:
    if not raw or not raw.isdigit():
        raise ValueError("setup_required: TENCENT_ADS_ACCOUNT_ID must be an integer string")
    return str(int(raw))


def runtime_config(facts: dict, require_account: bool) -> dict:
    token = env_value("TENCENT_ADS_ACCESS_TOKEN")
    account = env_value("TENCENT_ADS_ACCOUNT_ID")
    base_raw = env_value("TENCENT_ADS_API_BASE") or facts["productionAdgroupsBase"]
    missing = []
    if not token:
        missing.append("TENCENT_ADS_ACCESS_TOKEN")
    if require_account and not account:
        missing.append("TENCENT_ADS_ACCOUNT_ID")
    if missing:
        raise ValueError("setup_required: missing " + ", ".join(missing))
    base = allowed_base(base_raw, facts)
    parsed = {
        "accessToken": token,
        "apiBase": base,
        "userToken": env_value("TENCENT_ADS_USER_TOKEN"),
    }
    if account:
        parsed["accountId"] = account_id_value(account)
    return parsed


def auth_query(token: str, user_token: str) -> list[tuple[str, str]]:
    pairs = [
        ("access_token", token),
        ("timestamp", str(int(time.time()))),
        ("nonce", new_nonce()),
    ]
    if user_token:
        pairs.append(("user_token", user_token))
    return pairs


def encode_query(pairs: list[tuple[str, str]]) -> str:
    return urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)


def build_url(base: str, path: str, pairs: list[tuple[str, str]]) -> str:
    return base + path + "?" + encode_query(pairs)


def read_body_file(path: str) -> dict:
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError("usage: --body must be an existing JSON object file")
    if file_path.stat().st_size > 262144:
        raise ValueError("usage: --body exceeds 262144 bytes")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("usage: --body must be a JSON object")
    return payload


def validate_smart_fields(payload, facts: dict, goal_values: set[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "smart_bid_type" and value not in facts["smartBidType"]:
                raise ValueError("usage: smart_bid_type is not in the pinned enum")
            if key == "smart_targeting_mode" and value not in facts["smartTargetingMode"]:
                raise ValueError("usage: smart_targeting_mode is not in the pinned enum")
            if key == "smart_delivery_goal" and value not in goal_values:
                raise ValueError("usage: smart_delivery_goal is not in the pinned enum")
            if key == "is_smart_delivery_upgrade_project" and not isinstance(value, bool):
                raise ValueError("usage: is_smart_delivery_upgrade_project must be boolean")
            validate_smart_fields(value, facts, goal_values)
    elif isinstance(payload, list):
        for item in payload:
            validate_smart_fields(item, facts, goal_values)


def apply_account_id(payload: dict, account_id: str) -> dict:
    body = dict(payload)
    if "account_id" not in body:
        body["account_id"] = int(account_id)
    elif str(body["account_id"]) != str(int(account_id)):
        raise ValueError("usage: body account_id does not match TENCENT_ADS_ACCOUNT_ID")
    else:
        body["account_id"] = int(account_id)
    return body


def call_json(method: str, url: str, body: dict | None, opener, timeout: int) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        response = opener(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = try_json(raw)
        return {
            "httpStatus": exc.code,
            "body": parsed if parsed is not None else raw.decode("utf-8", errors="replace"),
        }
    except OSError as exc:
        raise RuntimeError(f"transport_error: {exc}") from exc
    try:
        raw = response.read()
        status = getattr(response, "status", None) or response.getcode()
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    parsed = try_json(raw)
    return {
        "httpStatus": status,
        "body": parsed if parsed is not None else raw.decode("utf-8", errors="replace"),
    }


def try_json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def api_exit(result: dict) -> int:
    body = result.get("body")
    if isinstance(body, dict) and body.get("code") == 0 and result.get("httpStatus", 500) < 300:
        return 0
    return 3


def redact_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    redacted = [
        (key, "<redacted>" if key in {"access_token", "client_secret", "refresh_token", "authorization_code"} else value)
        for key, value in query
    ]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(redacted)))


def cmd_status(facts: dict) -> int:
    missing = []
    if not env_value("TENCENT_ADS_ACCESS_TOKEN"):
        missing.append("TENCENT_ADS_ACCESS_TOKEN")
    if not env_value("TENCENT_ADS_ACCOUNT_ID"):
        missing.append("TENCENT_ADS_ACCOUNT_ID")
    base_raw = env_value("TENCENT_ADS_API_BASE") or facts["productionAdgroupsBase"]
    try:
        base = allowed_base(base_raw, facts)
        base_error = None
    except ValueError as exc:
        base = None
        base_error = str(exc)
        missing.append("TENCENT_ADS_API_BASE")
    available = not missing
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "function": "腾讯广告智能投放",
            "available": available,
            "state": "ready" if available else "setup_required",
            "missing": missing,
            "apiBase": base,
            "baseError": base_error,
            "readEndpoint": facts["adgroupsGet"]["method"] + " " + facts["adgroupsGet"]["path"],
            "liveDelivery": False,
            "credentialsPrinted": False,
        },
        0 if available else 2,
    )


def cmd_goals(facts: dict) -> int:
    values = goals()
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "source": facts["sdk"]["commit"],
            "model": "SmartDeliveryGoal",
            "comment": "场景化投放目标",
            "count": len(values),
            "values": values,
            "liveApi": False,
        },
        0,
    )


def cmd_adgroups_get(facts: dict, opener, page: str | None, page_size: str | None) -> int:
    config = runtime_config(facts, require_account=True)
    pairs = [("account_id", config["accountId"])]
    if page:
        if not page.isdigit() or int(page) < 1:
            raise ValueError("usage: --page must be a positive integer")
        pairs.append(("page", str(int(page))))
    if page_size:
        if not page_size.isdigit() or int(page_size) < 1:
            raise ValueError("usage: --page-size must be a positive integer")
        pairs.append(("page_size", str(int(page_size))))
    pairs.append(("fields", json.dumps(facts["defaultGetFields"], separators=(",", ":"))))
    pairs.extend(auth_query(config["accessToken"], config["userToken"]))
    url = build_url(config["apiBase"], facts["adgroupsGet"]["path"], pairs)
    result = call_json(facts["adgroupsGet"]["method"], url, None, opener, 30)
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "function": "腾讯广告智能投放",
            "operation": "adgroups-get",
            "requestUrl": redact_url(url),
            "httpStatus": result["httpStatus"],
            "body": result["body"],
            "liveDelivery": True,
        },
        api_exit(result),
    )


def cmd_write(facts: dict, operation: str, body_path: str, execute: bool, opener) -> int:
    spec = facts[operation]
    config = runtime_config(facts, require_account=True)
    payload = apply_account_id(read_body_file(body_path), config["accountId"])
    validate_smart_fields(payload, facts, set(goals()))
    pairs = auth_query(config["accessToken"], config["userToken"])
    url = build_url(config["apiBase"], spec["path"], pairs)
    if not execute:
        return emit(
            {
                "stableId": "proto:market:腾讯广告",
                "function": "腾讯广告智能投放",
                "operation": operation,
                "state": "execution_required",
                "requestUrl": redact_url(url),
                "method": spec["method"],
                "body": payload,
                "liveDelivery": False,
                "networkCalled": False,
            },
            2,
        )
    result = call_json(spec["method"], url, payload, opener, 30)
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "function": "腾讯广告智能投放",
            "operation": operation,
            "requestUrl": redact_url(url),
            "httpStatus": result["httpStatus"],
            "body": result["body"],
            "liveDelivery": True,
        },
        api_exit(result),
    )


def cmd_oauth_token(facts: dict, grant_type: str, opener) -> int:
    client_id = env_value("TENCENT_ADS_CLIENT_ID")
    client_secret = env_value("TENCENT_ADS_CLIENT_SECRET")
    missing = []
    if not client_id:
        missing.append("TENCENT_ADS_CLIENT_ID")
    if not client_secret:
        missing.append("TENCENT_ADS_CLIENT_SECRET")
    pairs = []
    if grant_type == "authorization_code":
        code = env_value("TENCENT_ADS_AUTHORIZATION_CODE")
        redirect = env_value("TENCENT_ADS_REDIRECT_URI")
        if not code:
            missing.append("TENCENT_ADS_AUTHORIZATION_CODE")
        if not redirect:
            missing.append("TENCENT_ADS_REDIRECT_URI")
        pairs = [
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("grant_type", "authorization_code"),
            ("authorization_code", code),
            ("redirect_uri", redirect),
        ]
    elif grant_type == "refresh_token":
        refresh = env_value("TENCENT_ADS_REFRESH_TOKEN")
        if not refresh:
            missing.append("TENCENT_ADS_REFRESH_TOKEN")
        pairs = [
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("grant_type", "refresh_token"),
            ("refresh_token", refresh),
        ]
    else:
        raise ValueError("usage: grant_type must be authorization_code or refresh_token")
    if missing:
        raise ValueError("setup_required: missing " + ", ".join(missing))
    url = facts["oauthTokenUrl"] + "?" + encode_query(pairs)
    result = call_json("GET", url, None, opener, 30)
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "operation": "oauth-token",
            "requestUrl": redact_url(url),
            "httpStatus": result["httpStatus"],
            "body": result["body"],
            "liveDelivery": False,
        },
        api_exit(result),
    )


def cmd_probe(facts: dict, opener) -> int:
    pairs = [
        ("account_id", "0"),
        ("fields", json.dumps(facts["defaultGetFields"], separators=(",", ":"))),
        ("access_token", ""),
        ("timestamp", str(int(time.time()))),
        ("nonce", new_nonce()),
    ]
    url = build_url(facts["productionAdgroupsBase"], facts["adgroupsGet"]["path"], pairs)
    result = call_json("GET", url, None, opener, 30)
    return emit(
        {
            "stableId": "proto:market:腾讯广告",
            "operation": "probe-host",
            "requestUrl": url,
            "httpStatus": result["httpStatus"],
            "body": result["body"],
            "liveDelivery": False,
            "credentialUsed": False,
        },
        0 if result.get("httpStatus") else 1,
    )


def parse_args(argv: list[str]) -> dict:
    if not argv:
        raise ValueError("usage: status | goals | adgroups-get | adgroups-add | adgroups-update | oauth-token | probe-host")
    command = argv[0]
    options = {"command": command, "execute": False, "body": None, "page": None, "page_size": None, "grant_type": "authorization_code"}
    index = 1
    while index < len(argv):
        item = argv[index]
        if item == "--execute":
            options["execute"] = True
            index += 1
            continue
        if item in {"--body", "--page", "--page-size", "--grant-type"}:
            if index + 1 >= len(argv):
                raise ValueError(f"usage: {item} requires a value")
            key = {"--body": "body", "--page": "page", "--page-size": "page_size", "--grant-type": "grant_type"}[item]
            options[key] = argv[index + 1]
            index += 2
            continue
        raise ValueError(f"usage: unknown argument {item}")
    return options


def main(argv: list[str] | None = None, opener=None) -> int:
    opener = opener or urllib.request.urlopen
    try:
        facts = pin()
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        command = options["command"]
        if command == "status":
            return cmd_status(facts)
        if command == "goals":
            return cmd_goals(facts)
        if command == "adgroups-get":
            return cmd_adgroups_get(facts, opener, options["page"], options["page_size"])
        if command == "adgroups-add":
            if not options["body"]:
                raise ValueError("usage: adgroups-add requires --body")
            return cmd_write(facts, "adgroupsAdd", options["body"], options["execute"], opener)
        if command == "adgroups-update":
            if not options["body"]:
                raise ValueError("usage: adgroups-update requires --body")
            return cmd_write(facts, "adgroupsUpdate", options["body"], options["execute"], opener)
        if command == "oauth-token":
            return cmd_oauth_token(facts, options["grant_type"], opener)
        if command == "probe-host":
            return cmd_probe(facts, opener)
        raise ValueError("usage: unknown command")
    except ValueError as exc:
        message = str(exc)
        state = "setup_required" if message.startswith("setup_required") else "usage_error"
        return emit(
            {
                "stableId": "proto:market:腾讯广告",
                "state": state,
                "message": message,
                "liveDelivery": False,
                "networkCalled": False,
            },
            2 if state == "setup_required" else 1,
        )
    except RuntimeError as exc:
        return emit(
            {
                "stableId": "proto:market:腾讯广告",
                "state": "transport_error",
                "message": str(exc),
                "liveDelivery": False,
            },
            1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
