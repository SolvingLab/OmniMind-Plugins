"""Callable adapter for 百度网盘 cloud file management.

Endpoints are the official open-platform URLs pinned in SOURCE.json.
Missing credentials return unavailable and do not call the file API.
"""

from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Callable, Mapping

PRODUCT = "百度网盘"
STABLE_ID = "proto:market:百度网盘"
FUNCTION = "云端文件与资料管理"
USER_AGENT = "pan.baidu.com"

OAUTH_AUTHORIZE = "https://openapi.baidu.com/oauth/2.0/authorize"
OAUTH_TOKEN = "https://openapi.baidu.com/oauth/2.0/token"
OAUTH_DEVICE_CODE = "https://openapi.baidu.com/oauth/2.0/device/code"
XPAN_FILE = "https://pan.baidu.com/rest/2.0/xpan/file"
XPAN_NAS = "https://pan.baidu.com/rest/2.0/xpan/nas"
XPAN_MULTIMEDIA = "https://pan.baidu.com/rest/2.0/xpan/multimedia"
QUOTA_URL = "https://pan.baidu.com/api/quota"
LOCATE_UPLOAD_URL = "https://d.pcs.baidu.com/rest/2.0/pcs/file"
LOCATE_APPID = "250528"
UPLOAD_VERSION = "2.0"
OFFICIAL_MCP_SSE = "https://mcp-pan.baidu.com/sse"
# Personal MCP authorize URL published on the official custom-agent page.
OFFICIAL_MCP_AUTHORIZE_URL = (
    "https://openapi.baidu.com/oauth/2.0/authorize"
    "?response_type=token"
    "&client_id=QHOuRXiepJBMjtk0esLhrPoNlQyYd0mF"
    "&redirect_uri=oob"
    "&scope=basic,netdisk"
    "&qrcode=1"
)
SCOPE = "basic,netdisk"
# Official slice page, fetched 2026-10-15: ordinary users have a fixed 4 MB
# slice, a file of at most 4 MB is one upload, and a non-final slice must
# reach that size (errno 31299). The page does not print a decimal byte count.
# 4 * 1024 * 1024 is that binary 4 MB. It stays within the ordinary-user cap
# and under the higher member caps, so this package does not add a membership
# slice selector.
SLICE_SIZE = 4 * 1024 * 1024
LIST_LIMIT_MAX = 1000
SEARCH_KEY_MAX_CHARS = 30

ENV_ACCESS_TOKEN = "BAIDU_NETDISK_ACCESS_TOKEN"
ENV_APP_KEY = "BAIDU_NETDISK_APP_KEY"
ENV_SECRET_KEY = "BAIDU_NETDISK_SECRET_KEY"
ENV_REDIRECT_URI = "BAIDU_NETDISK_REDIRECT_URI"
ENV_REFRESH_TOKEN = "BAIDU_NETDISK_REFRESH_TOKEN"
ENV_APP_DIR = "BAIDU_NETDISK_APP_DIR"
ENV_APP_ID = "BAIDU_NETDISK_APP_ID"

ALLOWED_API_HOSTS = {
    "openapi.baidu.com",
    "pan.baidu.com",
    "d.pcs.baidu.com",
    "mcp-pan.baidu.com",
}


@dataclass(frozen=True)
class Config:
    access_token: str = ""
    app_key: str = ""
    secret_key: str = ""
    redirect_uri: str = ""
    refresh_token: str = ""
    app_dir: str = ""
    app_id: str = ""

    def secrets(self) -> list[str]:
        values = [
            self.access_token,
            self.app_key,
            self.secret_key,
            self.refresh_token,
        ]
        return [item for item in values if len(item) >= 6]

    def presence(self) -> dict[str, bool]:
        return {
            "access_token": bool(self.access_token),
            "app_key": bool(self.app_key),
            "secret_key": bool(self.secret_key),
            "redirect_uri": bool(self.redirect_uri),
            "refresh_token": bool(self.refresh_token),
            "app_dir": bool(self.app_dir),
            "app_id": bool(self.app_id),
        }


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes = b""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass
class Result:
    exit_code: int
    payload: dict


def config_from_env(env: Mapping[str, str]) -> Config:
    def read(name: str) -> str:
        return str(env.get(name, "")).strip()

    return Config(
        access_token=read(ENV_ACCESS_TOKEN),
        app_key=read(ENV_APP_KEY),
        secret_key=read(ENV_SECRET_KEY),
        redirect_uri=read(ENV_REDIRECT_URI),
        refresh_token=read(ENV_REFRESH_TOKEN),
        app_dir=read(ENV_APP_DIR),
        app_id=read(ENV_APP_ID),
    )


def redact(text: str, secrets: list[str]) -> str:
    redacted = text
    for secret in secrets:
        redacted = redacted.replace(secret, "[redacted]")
    return redacted


def unavailable(reason: str, config: Config, detail: str) -> Result:
    return Result(
        2,
        {
            "ok": False,
            "state": "unavailable",
            "reason": reason,
            "detail": detail,
            "product": PRODUCT,
            "stableId": STABLE_ID,
            "function": FUNCTION,
            "configured": config.presence(),
            "upstreamCalled": False,
        },
    )


def local_ok(operation: str, config: Config, extra: dict) -> Result:
    payload = {
        "ok": True,
        "state": "local",
        "operation": operation,
        "product": PRODUCT,
        "stableId": STABLE_ID,
        "function": FUNCTION,
        "upstreamCalled": False,
        "configured": config.presence(),
    }
    payload.update(extra)
    return Result(0, payload)


def _query(params: Mapping[str, object]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        pairs.append((key, str(value)))
    return urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote, safe="")


def build_url(base: str, params: Mapping[str, object]) -> str:
    parts = urllib.parse.urlsplit(base)
    if parts.scheme != "https":
        raise ValueError(f"refusing non-https API URL: {parts.scheme}")
    if parts.hostname not in ALLOWED_API_HOSTS:
        raise ValueError(f"refusing unexpected API host: {parts.hostname}")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, _query(params), ""))


def form_body(params: Mapping[str, object]) -> bytes:
    return _query(params).encode("utf-8")


def json_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def absolute_cloud_path(path: str) -> str | None:
    if not path.startswith("/") or path.startswith("//"):
        return None
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts[1:]):
        return None
    return path


def apps_path(path: str, app_dir: str) -> str | None:
    cleaned = absolute_cloud_path(path)
    if cleaned is None or not (cleaned == "/apps" or cleaned.startswith("/apps/")):
        return None
    if app_dir:
        root = absolute_cloud_path(app_dir)
        if root is None or not (root == "/apps" or root.startswith("/apps/")):
            return None
        if cleaned != root and not cleaned.startswith(root.rstrip("/") + "/"):
            return None
    return cleaned


def _decode_json(body: bytes) -> tuple[dict | None, str]:
    text = body.decode("utf-8", "replace")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, text
    if not isinstance(parsed, dict):
        return None, text
    return parsed, text


def _code_ok(value: object) -> bool:
    return value in (None, 0, "0")


def upstream_success(payload: dict, operation: str) -> bool:
    if operation == "upload-slice":
        md5 = payload.get("md5")
        return _code_ok(payload.get("errno")) and _code_ok(payload.get("error_code")) and isinstance(md5, str) and len(md5) == 32
    if operation == "locateupload":
        return _code_ok(payload.get("errno")) and _code_ok(payload.get("error_code")) and bool(payload.get("servers"))
    if "errno" in payload:
        return payload.get("errno") in (0, "0")
    if "error_code" in payload:
        return payload.get("error_code") in (0, "0")
    return False


class UrllibTransport:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.context = ssl.create_default_context()

    def exchange(self, request: HttpRequest) -> HttpResponse:
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self.context),
            _NoRedirectHandler(),
        )
        http_request = urllib.request.Request(
            request.url,
            data=request.body if request.method != "GET" else None,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with opener.open(http_request, timeout=self.timeout) as response:
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except urllib.error.HTTPError as exc:
            return HttpResponse(
                status=exc.code,
                headers=dict(exc.headers.items()) if exc.headers else {},
                body=exc.read(),
            )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def call_upstream(
    transport: Callable[[HttpRequest], HttpResponse],
    request: HttpRequest,
    config: Config,
    operation: str,
) -> Result:
    try:
        response = transport(request)
    except Exception as exc:  # network and TLS failures stay truthful
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_error",
                "operation": operation,
                "product": PRODUCT,
                "stableId": STABLE_ID,
                "function": FUNCTION,
                "upstreamCalled": True,
                "detail": redact(f"{type(exc).__name__}: {exc}", config.secrets()),
            },
        )
    parsed, text = _decode_json(response.body)
    snippet = redact(text[:500], config.secrets())
    if parsed is None:
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_error",
                "operation": operation,
                "product": PRODUCT,
                "stableId": STABLE_ID,
                "function": FUNCTION,
                "upstreamCalled": True,
                "httpStatus": response.status,
                "detail": "upstream body was not a JSON object",
                "bodySnippet": snippet,
            },
        )
    ok = response.status == 200 and upstream_success(parsed, operation)
    return Result(
        0 if ok else 1,
        {
            "ok": ok,
            "state": "upstream" if ok else "upstream_rejected",
            "operation": operation,
            "product": PRODUCT,
            "stableId": STABLE_ID,
            "function": FUNCTION,
            "upstreamCalled": True,
            "httpStatus": response.status,
            "upstream": parsed,
        },
    )


def require_token(config: Config) -> Result | None:
    if config.access_token:
        return None
    return unavailable(
        "setup_required",
        config,
        "BAIDU_NETDISK_ACCESS_TOKEN is empty. No Baidu account is contacted.",
    )


def authorize_url(config: Config, mode: str) -> Result:
    if mode == "official-mcp":
        return local_ok(
            "authorize-url",
            config,
            {
                "mode": "official-mcp",
                "url": OFFICIAL_MCP_AUTHORIZE_URL,
                "detail": "Official personal MCP authorize page. This prints a URL only; it does not return a token.",
            },
        )
    if mode != "code":
        return unavailable("invalid_argument", config, "authorize mode must be code or official-mcp")
    if not config.app_key or not config.redirect_uri:
        return unavailable(
            "setup_required",
            config,
            "Authorization-code URL needs BAIDU_NETDISK_APP_KEY and BAIDU_NETDISK_REDIRECT_URI.",
        )
    params: dict[str, object] = {
        "response_type": "code",
        "client_id": config.app_key,
        "redirect_uri": config.redirect_uri,
        "scope": SCOPE,
    }
    if config.app_id:
        params["device_id"] = config.app_id
    return local_ok(
        "authorize-url",
        config,
        {
            "mode": "code",
            "url": build_url(OAUTH_AUTHORIZE, params),
            "detail": "Official authorization-code URL. The code is single-use and expires in 10 minutes.",
        },
    )


def _safe_exchange(transport, request: HttpRequest, config: Config, operation: str) -> HttpResponse | Result:
    try:
        return transport(request)
    except Exception as exc:
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_error",
                "operation": operation,
                "product": PRODUCT,
                "stableId": STABLE_ID,
                "function": FUNCTION,
                "upstreamCalled": True,
                "detail": redact(f"{type(exc).__name__}: {exc}", config.secrets()),
            },
        )


def _oauth_result(response: HttpResponse, config: Config, operation: str) -> Result:
    parsed, text = _decode_json(response.body)
    snippet = redact(text[:500], config.secrets())
    if parsed is None:
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_error",
                "operation": operation,
                "product": PRODUCT,
                "upstreamCalled": True,
                "httpStatus": response.status,
                "detail": "token endpoint did not return a JSON object",
                "bodySnippet": snippet,
            },
        )
    if operation == "device-code":
        ok = response.status == 200 and bool(parsed.get("device_code")) and not parsed.get("error")
        return Result(
            0 if ok else 1,
            {
                "ok": ok,
                "state": "upstream" if ok else "upstream_rejected",
                "operation": operation,
                "product": PRODUCT,
                "upstreamCalled": True,
                "httpStatus": response.status,
                "upstream": parsed,
                "detail": "One device-code response. This adapter does not poll.",
            },
        )
    ok = response.status == 200 and not parsed.get("error") and bool(parsed.get("access_token"))
    return Result(
        0 if ok else 1,
        {
            "ok": ok,
            "state": "upstream" if ok else "upstream_rejected",
            "operation": operation,
            "product": PRODUCT,
            "upstreamCalled": True,
            "httpStatus": response.status,
            "upstream": parsed,
            "detail": "Token response contains credentials when ok is true. Store them in user config; do not commit them.",
        },
    )


def exchange_code(config: Config, code: str, transport) -> Result:
    if not code or not config.app_key or not config.secret_key or not config.redirect_uri:
        return unavailable(
            "setup_required",
            config,
            "exchange-code needs a code, AppKey, SecretKey, and the same redirect URI used to request the code.",
        )
    request = HttpRequest(
        "GET",
        build_url(
            OAUTH_TOKEN,
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": config.app_key,
                "client_secret": config.secret_key,
                "redirect_uri": config.redirect_uri,
            },
        ),
        json_headers(),
    )
    response = _safe_exchange(transport, request, config, "exchange-code")
    if isinstance(response, Result):
        return response
    return _oauth_result(response, config, "exchange-code")


def refresh_token(config: Config, transport) -> Result:
    if not config.refresh_token or not config.app_key or not config.secret_key:
        return unavailable(
            "setup_required",
            config,
            "refresh needs BAIDU_NETDISK_REFRESH_TOKEN, APP_KEY, and SECRET_KEY.",
        )
    request = HttpRequest(
        "GET",
        build_url(
            OAUTH_TOKEN,
            {
                "grant_type": "refresh_token",
                "refresh_token": config.refresh_token,
                "client_id": config.app_key,
                "client_secret": config.secret_key,
            },
        ),
        json_headers(),
    )
    response = _safe_exchange(transport, request, config, "refresh-token")
    if isinstance(response, Result):
        return response
    return _oauth_result(response, config, "refresh-token")


def device_code(config: Config, transport) -> Result:
    if not config.app_key:
        return unavailable("setup_required", config, "device-code needs BAIDU_NETDISK_APP_KEY.")
    request = HttpRequest(
        "GET",
        build_url(
            OAUTH_DEVICE_CODE,
            {
                "response_type": "device_code",
                "client_id": config.app_key,
                "scope": SCOPE,
            },
        ),
        json_headers(),
    )
    response = _safe_exchange(transport, request, config, "device-code")
    if isinstance(response, Result):
        return response
    return _oauth_result(response, config, "device-code")


def device_token(config: Config, device_code_value: str, transport) -> Result:
    if not device_code_value or not config.app_key or not config.secret_key:
        return unavailable(
            "setup_required",
            config,
            "device-token needs the device code, AppKey, and SecretKey. This command performs one request and does not poll.",
        )
    request = HttpRequest(
        "GET",
        build_url(
            OAUTH_TOKEN,
            {
                "grant_type": "device_token",
                "code": device_code_value,
                "client_id": config.app_key,
                "client_secret": config.secret_key,
            },
        ),
        json_headers(),
    )
    response = _safe_exchange(transport, request, config, "device-token")
    if isinstance(response, Result):
        return response
    return _oauth_result(response, config, "device-token")


def quota(config: Config, transport) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    request = HttpRequest(
        "GET",
        build_url(
            QUOTA_URL,
            {
                "access_token": config.access_token,
                "checkfree": 1,
                "checkexpire": 1,
            },
        ),
        json_headers(),
    )
    return call_upstream(transport, request, config, "quota")


def uinfo(config: Config, transport) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    request = HttpRequest(
        "GET",
        build_url(
            XPAN_NAS,
            {
                "method": "uinfo",
                "access_token": config.access_token,
                "vip_version": "v2",
            },
        ),
        json_headers(),
    )
    return call_upstream(transport, request, config, "uinfo")


def status(config: Config, transport) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    user = uinfo(config, transport)
    space = quota(config, transport)
    ok = user.exit_code == 0 and space.exit_code == 0
    return Result(
        0 if ok else 1,
        {
            "ok": ok,
            "state": "upstream" if ok else "upstream_rejected",
            "operation": "status",
            "product": PRODUCT,
            "stableId": STABLE_ID,
            "function": FUNCTION,
            "upstreamCalled": True,
            "configured": config.presence(),
            "uinfo": user.payload.get("upstream"),
            "quota": space.payload.get("upstream"),
            "uinfoState": user.payload.get("state"),
            "quotaState": space.payload.get("state"),
        },
    )


def list_dir(
    config: Config,
    transport,
    directory: str,
    start: int,
    limit: int,
    order: str,
    desc: int,
) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    cleaned = absolute_cloud_path(directory)
    if cleaned is None:
        return unavailable("invalid_argument", config, "dir must be an absolute cloud path without . or ..")
    if order not in {"name", "time", "size"}:
        return unavailable("invalid_argument", config, "order must be name, time, or size")
    if start < 0 or limit < 1 or limit > LIST_LIMIT_MAX or desc not in {0, 1}:
        return unavailable("invalid_argument", config, "start, limit, or desc is outside the documented range")
    request = HttpRequest(
        "GET",
        build_url(
            XPAN_FILE,
            {
                "method": "list",
                "access_token": config.access_token,
                "dir": cleaned,
                "order": order,
                "start": start,
                "limit": limit,
                "web": 1,
                "folder": 0,
                "desc": desc,
            },
        ),
        json_headers(),
    )
    return call_upstream(transport, request, config, "list")


def search(
    config: Config,
    transport,
    key: str,
    directory: str,
    category: int | None,
    recursion: bool,
) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    if not key or len(key) > SEARCH_KEY_MAX_CHARS:
        return unavailable(
            "invalid_argument",
            config,
            "search key is required and must be at most 30 characters",
        )
    cleaned = absolute_cloud_path(directory)
    if cleaned is None:
        return unavailable("invalid_argument", config, "search dir must be an absolute cloud path")
    if category is not None and category not in {1, 2, 3, 4, 5, 6, 7}:
        return unavailable("invalid_argument", config, "category must be 1 through 7")
    params: dict[str, object] = {
        "method": "search",
        "access_token": config.access_token,
        "key": key,
        "dir": cleaned,
        "web": 1,
    }
    if category is not None:
        params["category"] = category
    if recursion:
        params["recursion"] = 1
    request = HttpRequest("GET", build_url(XPAN_FILE, params), json_headers())
    return call_upstream(transport, request, config, "search")


def file_meta(config: Config, transport, path: str, fsid: str, dlink: bool) -> Result:
    missing = require_token(config)
    if missing:
        return missing
    if fsid:
        if not fsid.isdigit():
            return unavailable("invalid_argument", config, "fsid must be a decimal file id")
        request = HttpRequest(
            "GET",
            build_url(
                XPAN_MULTIMEDIA,
                {
                    "method": "filemetas",
                    "access_token": config.access_token,
                    "fsids": json.dumps([int(fsid)], separators=(",", ":")),
                    "dlink": 1 if dlink else 0,
                    "thumb": 1,
                },
            ),
            json_headers(),
        )
        return call_upstream(transport, request, config, "meta")
    cleaned = apps_path(path, config.app_dir)
    if cleaned is None:
        return unavailable(
            "invalid_argument",
            config,
            "meta by path must be under /apps/{appname}. Official file-manager notes limit method=meta to that directory.",
        )
    request = HttpRequest(
        "GET",
        build_url(
            XPAN_FILE,
            {
                "method": "meta",
                "access_token": config.access_token,
                "path": cleaned,
                "dlink": 1 if dlink else 0,
            },
        ),
        json_headers(),
    )
    return call_upstream(transport, request, config, "meta")


def _filemanager(
    config: Config,
    transport,
    opera: str,
    filelist: list,
    confirmed: bool,
) -> Result:
    if not confirmed:
        return unavailable(
            "confirmation_required",
            config,
            f"{opera} changes cloud files. Pass --yes only after the user explicitly asks for this change.",
        )
    missing = require_token(config)
    if missing:
        return missing
    params = {
        "method": "filemanager",
        "access_token": config.access_token,
        "opera": opera,
    }
    body = {
        "async": 0,
        "filelist": json.dumps(filelist, ensure_ascii=False, separators=(",", ":")),
    }
    if opera != "delete":
        body["ondup"] = "fail"
    request = HttpRequest(
        "POST",
        build_url(XPAN_FILE, params),
        {**json_headers(), "Content-Type": "application/x-www-form-urlencoded"},
        form_body(body),
    )
    return call_upstream(transport, request, config, opera)


def rename_path(config: Config, transport, path: str, newname: str, confirmed: bool) -> Result:
    cleaned = apps_path(path, config.app_dir)
    if cleaned is None or not newname or "/" in newname or newname in {".", ".."}:
        return unavailable("invalid_argument", config, "rename needs an /apps path and a single new file name")
    return _filemanager(
        config,
        transport,
        "rename",
        [{"path": cleaned, "newname": newname}],
        confirmed,
    )


def move_or_copy(
    config: Config,
    transport,
    opera: str,
    path: str,
    dest: str,
    newname: str,
    confirmed: bool,
) -> Result:
    source = apps_path(path, config.app_dir)
    target = apps_path(dest, config.app_dir)
    if source is None or target is None or not newname or "/" in newname:
        return unavailable(
            "invalid_argument",
            config,
            f"{opera} needs source, destination, and new name, all under /apps/{{appname}}",
        )
    return _filemanager(
        config,
        transport,
        opera,
        [{"path": source, "dest": target, "newname": newname}],
        confirmed,
    )


def delete_path(config: Config, transport, path: str, confirmed: bool) -> Result:
    cleaned = apps_path(path, config.app_dir)
    if cleaned is None or cleaned == "/apps":
        return unavailable("invalid_argument", config, "delete needs a file or folder under /apps/{appname}")
    return _filemanager(config, transport, "delete", [cleaned], confirmed)


def make_dir(config: Config, transport, path: str, confirmed: bool) -> Result:
    if not confirmed:
        return unavailable(
            "confirmation_required",
            config,
            "mkdir creates a cloud folder. Pass --yes only after the user explicitly asks.",
        )
    missing = require_token(config)
    if missing:
        return missing
    cleaned = apps_path(path, config.app_dir)
    if cleaned is None or cleaned == "/apps":
        return unavailable("invalid_argument", config, "mkdir path must be under /apps/{appname}")
    request = HttpRequest(
        "POST",
        build_url(
            XPAN_FILE,
            {"method": "create", "access_token": config.access_token},
        ),
        {**json_headers(), "Content-Type": "application/x-www-form-urlencoded"},
        form_body({"path": cleaned, "isdir": 1, "rtype": 0}),
    )
    return call_upstream(transport, request, config, "mkdir")


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _multipart(filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = "omnimind-baidu-netdisk-" + uuid.uuid4().hex
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body = head + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def _baidu_https_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower().rstrip(".")
    return host == "baidu.com" or host.endswith(".baidu.com") or host.endswith(".baidupcs.com") or host.endswith(".bcebos.com")


def _upload_origin(server: str) -> str | None:
    if not server or any(char in server for char in " \t\r\n"):
        return None
    if "://" not in server:
        server = "https://" + server
    parts = urllib.parse.urlsplit(server)
    if parts.scheme != "https" or parts.username or parts.password or not _baidu_https_host(parts.hostname):
        return None
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def slice_spans(size: int, slice_size: int = SLICE_SIZE) -> list[tuple[int, int]]:
    if size < 0 or slice_size < 1:
        raise ValueError("size and slice_size must be non-negative with a positive slice")
    if size == 0:
        return [(0, 0)]
    spans = []
    offset = 0
    while offset < size:
        end = min(offset + slice_size, size)
        spans.append((offset, end))
        offset = end
    return spans


def _read_span(local_path: str, content: bytes | None, start: int, end: int) -> bytes:
    if content is not None:
        return content[start:end]
    with open(local_path, "rb") as handle:
        handle.seek(start)
        return handle.read(end - start)


def _pending_partseqs(value: object, part_count: int) -> list[int] | None:
    if not isinstance(value, list):
        return None
    seqs: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            return None
        if item < 0 or item >= part_count or item in seqs:
            return None
        seqs.append(item)
    return seqs


def _upload_stopped(config: Config, uploadid: str, detail: str, uploaded: list[int], pending: list[int], upstream: dict | None = None) -> Result:
    payload = {
        "ok": False,
        "state": "upstream_rejected",
        "operation": "upload",
        "product": PRODUCT,
        "stableId": STABLE_ID,
        "function": FUNCTION,
        "upstreamCalled": True,
        "createCalled": False,
        "uploadid": uploadid,
        "uploadedPartseq": uploaded,
        "pendingPartseq": pending,
        "detail": redact(detail, config.secrets()),
    }
    if upstream is not None:
        payload["upstream"] = upstream
    return Result(1, payload)


def upload_file(
    config: Config,
    transport,
    local_path: str,
    cloud_path: str,
    content: bytes | None,
    confirmed: bool,
    resume_uploadid: str = "",
    slice_size: int = SLICE_SIZE,
) -> Result:
    if not confirmed:
        return unavailable(
            "confirmation_required",
            config,
            "upload writes a cloud file. Pass --yes only after the user explicitly asks.",
        )
    missing = require_token(config)
    if missing:
        return missing
    cleaned = apps_path(cloud_path, config.app_dir)
    if cleaned is None:
        return unavailable("invalid_argument", config, "upload path must be under /apps/{appname}")
    if slice_size < 1:
        return unavailable("invalid_argument", config, "slice size must be positive")
    size = len(content) if content is not None else os.path.getsize(local_path)
    spans = slice_spans(size, slice_size)
    local_md5 = [_md5(_read_span(local_path, content, start, end)) for start, end in spans]
    filename = cleaned.rsplit("/", 1)[-1]
    precreate_body: dict[str, object] = {
        "path": cleaned,
        "size": size,
        "isdir": 0,
        "block_list": json.dumps(local_md5, separators=(",", ":")),
        "autoinit": 1,
        "rtype": 0,
    }
    if resume_uploadid:
        precreate_body["uploadid"] = resume_uploadid
    precreate = call_upstream(
        transport,
        HttpRequest(
            "POST",
            build_url(XPAN_FILE, {"method": "precreate", "access_token": config.access_token}),
            {**json_headers(), "Content-Type": "application/x-www-form-urlencoded"},
            form_body(precreate_body),
        ),
        config,
        "precreate",
    )
    if precreate.exit_code != 0:
        precreate.payload["createCalled"] = False
        return precreate
    upstream = precreate.payload.get("upstream") or {}
    uploadid = upstream.get("uploadid")
    if not isinstance(uploadid, str) or not uploadid:
        return _upload_stopped(config, "", "precreate did not return uploadid", [], [], upstream)
    pending = _pending_partseqs(upstream.get("block_list"), len(spans))
    if pending is None:
        return _upload_stopped(
            config,
            uploadid,
            "precreate block_list was missing or not a list of slice indexes, so create was not called",
            [],
            [],
            upstream,
        )
    uploaded_partseq: list[int] = []
    returned_md5: dict[int, str] = {}
    if pending:
        locate = call_upstream(
            transport,
            HttpRequest(
                "GET",
                build_url(
                    LOCATE_UPLOAD_URL,
                    {
                        "method": "locateupload",
                        "appid": LOCATE_APPID,
                        "access_token": config.access_token,
                        "path": cleaned,
                        "uploadid": uploadid,
                        "upload_version": UPLOAD_VERSION,
                    },
                ),
                json_headers(),
            ),
            config,
            "locateupload",
        )
        if locate.exit_code != 0:
            locate.payload["createCalled"] = False
            locate.payload["uploadid"] = uploadid
            return locate
        servers = (locate.payload.get("upstream") or {}).get("servers") or []
        origin = None
        if servers and isinstance(servers[0], dict):
            origin = _upload_origin(str(servers[0].get("server", "")))
        if origin is None:
            return _upload_stopped(config, uploadid, "locateupload did not return an https upload server", [], pending)
        for partseq in pending:
            start, end = spans[partseq]
            chunk = _read_span(local_path, content, start, end)
            body, content_type = _multipart(filename, chunk)
            uploaded = call_upstream(
                transport,
                HttpRequest(
                    "POST",
                    origin
                    + "/rest/2.0/pcs/superfile2?"
                    + _query(
                        {
                            "method": "upload",
                            "type": "tmpfile",
                            "access_token": config.access_token,
                            "path": cleaned,
                            "uploadid": uploadid,
                            "partseq": partseq,
                        }
                    ),
                    {"User-Agent": USER_AGENT, "Content-Type": content_type},
                    body,
                ),
                config,
                "upload-slice",
            )
            if uploaded.exit_code != 0:
                uploaded.payload["createCalled"] = False
                uploaded.payload["uploadid"] = uploadid
                uploaded.payload["uploadedPartseq"] = uploaded_partseq
                uploaded.payload["pendingPartseq"] = pending
                return uploaded
            returned = (uploaded.payload.get("upstream") or {}).get("md5")
            if returned != local_md5[partseq]:
                return _upload_stopped(
                    config,
                    uploadid,
                    f"slice {partseq} md5 did not match precreate block_list, so create was not called",
                    uploaded_partseq,
                    pending,
                    uploaded.payload.get("upstream") if isinstance(uploaded.payload.get("upstream"), dict) else None,
                )
            returned_md5[partseq] = returned
            uploaded_partseq.append(partseq)
    create_blocks = [returned_md5.get(index, local_md5[index]) for index in range(len(spans))]
    final = call_upstream(
        transport,
        HttpRequest(
            "POST",
            build_url(XPAN_FILE, {"method": "create", "access_token": config.access_token}),
            {**json_headers(), "Content-Type": "application/x-www-form-urlencoded"},
            form_body(
                {
                    "path": cleaned,
                    "size": size,
                    "isdir": 0,
                    "block_list": json.dumps(create_blocks, separators=(",", ":")),
                    "uploadid": uploadid,
                    "rtype": 0,
                }
            ),
        ),
        config,
        "upload",
    )
    final.payload["createCalled"] = True
    final.payload["uploadid"] = uploadid
    final.payload["partCount"] = len(spans)
    final.payload["uploadedPartseq"] = uploaded_partseq
    if final.exit_code == 0:
        final.payload["localPath"] = local_path
    return final


def _dlink_from(payload: dict) -> str | None:
    candidates = []
    if isinstance(payload.get("dlink"), str):
        candidates.append(payload["dlink"])
    info = payload.get("info")
    if isinstance(info, dict) and isinstance(info.get("dlink"), str):
        candidates.append(info["dlink"])
    for item in payload.get("list") or []:
        if isinstance(item, dict) and isinstance(item.get("dlink"), str):
            candidates.append(item["dlink"])
    for item in candidates:
        parts = urllib.parse.urlsplit(item)
        if parts.scheme == "https" and parts.hostname:
            return item
    return None


def download_fsid(config: Config, transport, fsid: str, stream_to: Callable[[HttpRequest, str], int], output: str, confirmed: bool) -> Result:
    if not confirmed:
        return unavailable(
            "confirmation_required",
            config,
            "download writes a local file. Pass --yes only after the user explicitly asks.",
        )
    meta = file_meta(config, transport, "", fsid, True)
    if meta.exit_code != 0:
        return meta
    dlink = _dlink_from(meta.payload.get("upstream") or {})
    if not dlink:
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_rejected",
                "operation": "download",
                "product": PRODUCT,
                "upstreamCalled": True,
                "detail": "filemetas did not return an https dlink",
            },
        )
    dlink_parts = urllib.parse.urlsplit(dlink)
    if not _baidu_https_host(dlink_parts.hostname):
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_rejected",
                "operation": "download",
                "product": PRODUCT,
                "upstreamCalled": True,
                "detail": f"dlink host {dlink_parts.hostname} is outside baidu.com, baidupcs.com, and bcebos.com; token was not sent",
            },
        )
    separator = "&" if dlink_parts.query else "?"
    download_url = f"{dlink}{separator}access_token={urllib.parse.quote(config.access_token, safe='')}"
    request = HttpRequest("GET", download_url, {"User-Agent": USER_AGENT})
    try:
        written = stream_to(request, output)
    except Exception as exc:
        return Result(
            1,
            {
                "ok": False,
                "state": "upstream_error",
                "operation": "download",
                "product": PRODUCT,
                "upstreamCalled": True,
                "detail": redact(f"{type(exc).__name__}: {exc}", config.secrets()),
            },
        )
    return Result(
        0,
        {
            "ok": True,
            "state": "upstream",
            "operation": "download",
            "product": PRODUCT,
            "stableId": STABLE_ID,
            "function": FUNCTION,
            "upstreamCalled": True,
            "output": output,
            "bytes": written,
        },
    )


def probe_host(transport, timeout_sse: Callable[[], dict]) -> Result:
    config = Config()
    uinfo_request = HttpRequest(
        "GET",
        build_url(XPAN_NAS, {"method": "uinfo"}),
        json_headers(),
    )
    uinfo_result = call_upstream(transport, uinfo_request, config, "probe-uinfo")
    sse = timeout_sse()
    return Result(
        2,
        {
            "ok": False,
            "state": "probe",
            "operation": "probe-host",
            "product": PRODUCT,
            "stableId": STABLE_ID,
            "function": FUNCTION,
            "functionPass": False,
            "nativePass": False,
            "detail": "Host reachability only. No access token was sent. This is not cloud file management success.",
            "uinfo": {
                "httpStatus": uinfo_result.payload.get("httpStatus"),
                "state": uinfo_result.payload.get("state"),
                "errno": (uinfo_result.payload.get("upstream") or {}).get("errno")
                if isinstance(uinfo_result.payload.get("upstream"), dict)
                else None,
            },
            "mcpSse": sse,
        },
    )


def stream_download(request: HttpRequest, output: str, timeout: float = 30.0) -> int:
    parts = urllib.parse.urlsplit(request.url)
    if parts.scheme != "https":
        raise ValueError("download dlink must be https")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        _NoRedirectHandler(),
    )
    http_request = urllib.request.Request(request.url, headers=dict(request.headers), method="GET")
    written = 0
    with opener.open(http_request, timeout=timeout) as response, open(output, "wb") as handle:
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
    return written


def probe_sse(timeout: float = 8.0) -> dict:
    request = urllib.request.Request(
        OFFICIAL_MCP_SSE,
        headers={"Accept": "text/event-stream", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            sample = response.read(256)
            return {
                "url": OFFICIAL_MCP_SSE,
                "httpStatus": response.status,
                "sampleBytes": len(sample),
                "connected": False,
                "detail": "Unauthenticated GET returned. This does not mean the MCP session is authorized.",
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": OFFICIAL_MCP_SSE,
            "httpStatus": exc.code,
            "connected": False,
            "detail": "Unauthenticated SSE request was rejected or redirected by status. Not a function pass.",
        }
    except Exception as exc:
        return {
            "url": OFFICIAL_MCP_SSE,
            "connected": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
