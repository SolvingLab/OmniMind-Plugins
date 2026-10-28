"""Onshape cloud CAD adapter.

Local adapter, not an Onshape or PTC client. Read calls follow
onshape-public/apikey@52b6af963bc9a5c75859c93ff414914d4664941d.
Create, feature edit, import, and translation export follow the Onshape
REST API OpenAPI server https://cad.onshape.com/api/v17. Delete is
specification only and does not send a request. This package does not
create API keys or accounts.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

QUERY_PARAMS = (
    "query",
    "filter",
    "owner",
    "ownerType",
    "sortColumn",
    "sortOrder",
    "offset",
    "limit",
)
DOCUMENTS_PATH = "/api/documents"
API_V17 = "/api/v17"
OPENAPI_VERSION = "1.222.90730-c8d74e607a47"
NONCE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
ID_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
MAX_REDIRECTS = 3
BODY_LIMIT = 1024 * 1024
IMPORT_LIMIT = 32 * 1024 * 1024
IMPLEMENTED = (
    "documents",
    "mass-by-material",
    "export-stl",
    "create-document",
    "create-part-studio",
    "create-assembly",
    "get-features",
    "add-feature",
    "update-feature",
    "import-file",
    "upload-blob",
    "export-translation",
    "specify-delete",
)


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def setup(message: str) -> int:
    print("setup_required: " + message, file=sys.stderr)
    return 2


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def js_query_escape(value: str) -> str:
    return urllib.parse.quote(value, safe="-_.!~*'()")


def query_string(values: dict[str, str], order: tuple[str, ...] | None = None) -> str:
    names = order if order is not None else tuple(values)
    parts = []
    for name in names:
        if name in values:
            parts.append(js_query_escape(name) + "=" + js_query_escape(values[name]))
    return "&".join(parts)


def http_date(now: datetime) -> str:
    return (
        f"{WEEKDAYS[now.weekday()]}, {now.day:02d} {MONTHS[now.month - 1]} "
        f"{now.year:04d} {now.hour:02d}:{now.minute:02d}:{now.second:02d} GMT"
    )


def signature_string(method: str, nonce: str, stamp: str, content_type: str, path: str, query: str) -> str:
    return (
        method + "\n" + nonce + "\n" + stamp + "\n" + content_type + "\n" + path + "\n" + query + "\n"
    ).lower()


def authorization(
    method: str,
    path: str,
    query: str,
    access_key: str,
    secret_key: str,
    accept: str = "application/vnd.onshape.v1+json",
    nonce: str | None = None,
    stamp: str | None = None,
    content_type: str = "application/json",
) -> dict[str, str]:
    nonce = nonce or "".join(secrets.choice(NONCE_ALPHABET) for _ in range(25))
    stamp = stamp or http_date(datetime.now(timezone.utc))
    signed = signature_string(method, nonce, stamp, content_type, path, query)
    digest = hmac.new(secret_key.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("ascii")
    return {
        "Date": stamp,
        "On-Nonce": nonce,
        "Content-Type": content_type,
        "Accept": accept,
        "Authorization": "On " + access_key + ":HmacSHA256:" + signature,
    }


def origin(base_url: str) -> str | None:
    parsed = urllib.parse.urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    if parsed.path not in {"", "/"}:
        return None
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = "[" + host + "]"
    if parsed.port is not None:
        host = host + ":" + str(parsed.port)
    return parsed.scheme + "://" + host


def credentials() -> tuple[str, str, str] | int:
    access_key = os.environ.get("ONSHAPE_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("ONSHAPE_SECRET_KEY", "").strip()
    base_url = os.environ.get("ONSHAPE_BASE_URL", "").strip()
    if not access_key or not secret_key or not base_url:
        return setup(
            "ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY, and ONSHAPE_BASE_URL are required. "
            "No default and no key creation."
        )
    normalized = origin(base_url)
    if normalized is None:
        return setup(
            "ONSHAPE_BASE_URL must be an origin such as https://cad.onshape.com, with no user, path, or query."
        )
    return access_key, secret_key, normalized


def valid_id(value: str) -> bool:
    return 1 <= len(value) <= 128 and all(char in ID_OK for char in value)


def build_dwmve_path(resource: str, document_id: str, wvm: str, wvm_id: str, element_id: str, subresource: str = "") -> str:
    path = "/api/" + resource + "/d/" + document_id + "/" + wvm + "/" + wvm_id + "/e/" + element_id
    if subresource:
        path += "/" + subresource
    return path


def default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def host_allowed(configured_base: str, redirect_url: str) -> bool:
    configured = urllib.parse.urlsplit(configured_base)
    redirect = urllib.parse.urlsplit(redirect_url)
    if redirect.scheme != configured.scheme or redirect.hostname is None or redirect.username or redirect.password:
        return False
    configured_host = configured.hostname.lower().rstrip(".")
    redirect_host = redirect.hostname.lower().rstrip(".")
    configured_port = configured.port or default_port(configured.scheme)
    redirect_port = redirect.port or default_port(redirect.scheme)
    if redirect_host == configured_host and redirect_port == configured_port:
        return True
    family = configured_host == "onshape.com" or configured_host.endswith(".onshape.com")
    redirect_family = redirect_host == "onshape.com" or redirect_host.endswith(".onshape.com")
    return bool(
        family
        and redirect_family
        and redirect.scheme == "https"
        and redirect_port == 443
        and configured.scheme == "https"
    )


def read_bounded(response: object, limit: int = 32 * 1024 * 1024) -> bytes | None:
    chunks = []
    total = 0
    while True:
        chunk = response.read(64 * 1024)  # type: ignore[attr-defined]
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def request_get(
    base_url: str,
    path: str,
    query: str,
    access_key: str,
    secret_key: str,
    accept: str,
    follow_redirects: bool,
) -> tuple[bytes, int] | int:
    opener = urllib.request.build_opener(RejectRedirect)
    current_base = base_url
    current_path = path
    current_query = query
    for hop in range(MAX_REDIRECTS + 1):
        headers = authorization("GET", current_path, current_query, access_key, secret_key, accept)
        url = current_base + current_path + (("?" + current_query) if current_query else "")
        request = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with opener.open(request, timeout=30) as response:
                body = read_bounded(response)
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            location = exc.headers.get("Location") if follow_redirects and status == 307 else None
            exc.close()
            if location is None or hop == MAX_REDIRECTS:
                if status == 307 and follow_redirects and hop == MAX_REDIRECTS:
                    return fail("redirect_not_followed: redirect limit reached. Access key was not sent again.")
                return fail("http_status: " + str(status))
            redirected = urllib.parse.urljoin(url, location)
            parsed = urllib.parse.urlsplit(redirected)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                return fail("redirect_not_followed: redirect URL is not an origin path. Access key was not sent.")
            if not host_allowed(base_url, redirected):
                shown = parsed.hostname[:253]
                return fail(
                    "redirect_not_followed: host="
                    + shown
                    + " is outside the configured origin family. Access key was not sent."
                )
            if not parsed.path.startswith("/") or parsed.path.startswith("//") or "/.." in parsed.path:
                return fail("redirect_not_followed: redirect path is not a single absolute path. Access key was not sent.")
            current_base = parsed.scheme + "://" + parsed.netloc
            current_path = parsed.path
            current_query = node_reencode_query(parsed.query)
            continue
        except OSError:
            return setup("the configured Onshape origin did not accept a connection. No CAD write was sent.")
        if body is None:
            return fail("response_too_large: body was not printed.")
        if status != 200:
            return fail("http_status: " + str(status))
        return body, hop
    return fail("redirect_not_followed: redirect limit reached. Access key was not sent again.")


def node_reencode_query(raw: str) -> str:
    if not raw:
        return ""
    parts = []
    for piece in raw.split("&"):
        if not piece:
            continue
        name, separator, value = piece.partition("=")
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value) if separator else ""
        parts.append(js_query_escape(name) + "=" + js_query_escape(value))
    return "&".join(parts)


def write_body(body: bytes) -> int:
    sys.stdout.buffer.write(body)
    if not body.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")
    return 0


def documents(values: dict[str, str], creds: tuple[str, str, str]) -> int:
    access_key, secret_key, base_url = creds
    query = query_string(values, QUERY_PARAMS)
    result = request_get(
        base_url,
        DOCUMENTS_PATH,
        query,
        access_key,
        secret_key,
        "application/vnd.onshape.v1+json",
        False,
    )
    if isinstance(result, int):
        return result
    return write_body(result[0])


def tally_mass(parts: object, mass_properties: object) -> dict[str, object] | None:
    if not isinstance(parts, list) or not isinstance(mass_properties, dict):
        return None
    bodies = mass_properties.get("bodies")
    if not isinstance(bodies, dict):
        return None
    grouped: dict[str, list[str]] = {}
    for part in parts:
        if not isinstance(part, dict):
            return None
        material = part.get("material")
        if material is None:
            continue
        if not isinstance(material, dict) or "id" not in material or "partId" not in part:
            return None
        material_id = material["id"]
        part_id = part["partId"]
        if not isinstance(material_id, str) or not isinstance(part_id, str):
            return None
        grouped.setdefault(material_id, []).append(part_id)
    masses: dict[str, float] = {}
    total = 0.0
    for material_id, part_ids in grouped.items():
        masses[material_id] = 0.0
        for part_id in part_ids:
            body = bodies.get(part_id)
            if not isinstance(body, dict) or "hasMass" not in body:
                return None
            if body["hasMass"] is not True:
                continue
            mass = body.get("mass")
            if not isinstance(mass, list) or not mass or isinstance(mass[0], bool) or not isinstance(mass[0], (int, float)):
                return None
            masses[material_id] += float(mass[0])
            total += float(mass[0])
    return {"operation": "mass-by-material", "massesByMaterial": masses, "totalMass": total}


def wvm_from_args(args: argparse.Namespace) -> tuple[str, str] | int:
    chosen = [(name, getattr(args, name)) for name in ("workspace", "version", "microversion") if getattr(args, name)]
    if len(chosen) != 1 or not args.document or not args.element:
        return setup(
            "this command requires --document, --element, and exactly one of --workspace, --version, --microversion."
        )
    flag, value = chosen[0]
    wvm = {"workspace": "w", "version": "v", "microversion": "m"}[flag]
    if not valid_id(args.document) or not valid_id(args.element) or not valid_id(value):
        return setup("document, element, and workspace/version/microversion ids must be 1-128 alphanumeric characters.")
    return wvm, value


def mass_by_material(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    selected = wvm_from_args(args)
    if isinstance(selected, int):
        return selected
    wvm, wvm_id = selected
    access_key, secret_key, base_url = creds
    parts_path = build_dwmve_path("parts", args.document, wvm, wvm_id, args.element)
    parts_result = request_get(
        base_url,
        parts_path,
        "",
        access_key,
        secret_key,
        "application/vnd.onshape.v1+json",
        True,
    )
    if isinstance(parts_result, int):
        return parts_result
    mass_path = build_dwmve_path("partstudios", args.document, wvm, wvm_id, args.element, "massproperties")
    mass_result = request_get(
        base_url,
        mass_path,
        "massAsGroup=false",
        access_key,
        secret_key,
        "application/vnd.onshape.v1+json",
        True,
    )
    if isinstance(mass_result, int):
        return mass_result
    try:
        parts = json.loads(parts_result[0].decode("utf-8"))
        mass_properties = json.loads(mass_result[0].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return fail("response_shape: part or mass response was not JSON. Body was not printed.")
    tally = tally_mass(parts, mass_properties)
    if tally is None:
        return fail("response_shape: part or mass response did not match the pinned massByMaterial fields.")
    return write_body((json.dumps(tally, ensure_ascii=False) + "\n").encode("utf-8"))


def export_stl(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    if not args.document or not args.workspace or not args.element:
        return setup("export-stl requires --document, --workspace, and --element. Version and microversion are not in the pinned sample.")
    if not valid_id(args.document) or not valid_id(args.workspace) or not valid_id(args.element):
        return setup("document, workspace, and element ids must be 1-128 alphanumeric characters.")
    access_key, secret_key, base_url = creds
    path = build_dwmve_path("partstudios", args.document, "w", args.workspace, args.element, "stl")
    result = request_get(
        base_url,
        path,
        "",
        access_key,
        secret_key,
        "application/vnd.onshape.v1+octet-stream",
        True,
    )
    if isinstance(result, int):
        return result
    sys.stdout.buffer.write(result[0])
    return 0


def v17_path(suffix: str) -> str:
    return API_V17 + suffix


def plain_name(value: str) -> bool:
    if not value or len(value) > 256:
        return False
    return all(char.isprintable() and char not in "\r\n" for char in value)


def require_ids(pairs: list[tuple[str, str]]) -> int | None:
    for label, value in pairs:
        if not value or not valid_id(value):
            return setup(label + " must be 1-128 alphanumeric characters. No request was sent.")
    return None


def document_payload(name: str, public: bool, owner_type: int | None) -> dict[str, object]:
    payload: dict[str, object] = {"name": name, "isPublic": public}
    if owner_type is not None:
        payload["ownerType"] = owner_type
    return payload


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def request_exchange(
    method: str,
    base_url: str,
    path: str,
    query: str,
    body: bytes | None,
    access_key: str,
    secret_key: str,
    accept: str,
    content_type: str,
) -> tuple[bytes, int] | int:
    headers = authorization(
        method,
        path,
        query,
        access_key,
        secret_key,
        accept,
        content_type=content_type,
    )
    url = base_url + path + (("?" + query) if query else "")
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    opener = urllib.request.build_opener(RejectRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            payload = read_bounded(response)
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        return fail("http_status: " + str(status))
    except OSError:
        return setup("the configured Onshape origin did not accept a connection. No CAD write was completed.")
    if payload is None:
        return fail("response_too_large: body was not printed.")
    if status < 200 or status > 206:
        return fail("http_status: " + str(status))
    return payload, status


def post_json(path: str, payload: object, creds: tuple[str, str, str]) -> int:
    access_key, secret_key, base_url = creds
    result = request_exchange(
        "POST",
        base_url,
        path,
        "",
        json_bytes(payload),
        access_key,
        secret_key,
        "application/json",
        "application/json",
    )
    if isinstance(result, int):
        return result
    return write_body(result[0])


def create_document(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    if not plain_name(args.name or ""):
        return setup("create-document requires --name, 1-256 printable characters. No request was sent.")
    if args.owner_type is not None and args.owner_type not in {0, 1, 2}:
        return setup("ownerType must be 0, 1, or 2 as documented by the pinned client. No request was sent.")
    payload = document_payload(args.name, bool(args.public), args.owner_type)
    return post_json(v17_path("/documents"), payload, creds)


def create_part_studio(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace)])
    if rejected is not None:
        return rejected
    if args.name is not None and not plain_name(args.name):
        return setup("part studio name must be 1-256 printable characters. No request was sent.")
    payload: dict[str, object] = {} if not args.name else {"name": args.name}
    path = v17_path("/partstudios/d/" + args.document + "/w/" + args.workspace)
    return post_json(path, payload, creds)


def create_assembly(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace)])
    if rejected is not None:
        return rejected
    if not plain_name(args.name or ""):
        return setup("create-assembly requires --name. No request was sent.")
    path = v17_path("/assemblies/d/" + args.document + "/w/" + args.workspace)
    return post_json(path, {"name": args.name}, creds)


def get_features(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    selected = wvm_from_args(args)
    if isinstance(selected, int):
        return selected
    wvm, wvm_id = selected
    access_key, secret_key, base_url = creds
    path = v17_path("/partstudios/d/" + args.document + "/" + wvm + "/" + wvm_id + "/e/" + args.element + "/features")
    result = request_get(base_url, path, "", access_key, secret_key, "application/json", False)
    if isinstance(result, int):
        return result
    return write_body(result[0])


def load_feature_body(path: str) -> dict[str, object] | int:
    file_path = Path(path)
    if not file_path.is_file():
        return setup("feature body must be an existing file. No request was sent.")
    if file_path.stat().st_size > BODY_LIMIT:
        return setup("feature body is larger than 1 MiB. No request was sent.")
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return setup("feature body must be a UTF-8 JSON object. No request was sent.")
    if not isinstance(data, dict):
        return setup("feature body must be a JSON object for BTFeatureDefinitionCall-1406. No request was sent.")
    feature = data.get("feature")
    if feature is not None and not isinstance(feature, dict):
        return setup("feature must be a JSON object. No request was sent.")
    return data


def add_feature(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace), ("element", args.element)])
    if rejected is not None:
        return rejected
    if not args.body_file:
        return setup("add-feature requires --body-file. No request was sent.")
    payload = load_feature_body(args.body_file)
    if isinstance(payload, int):
        return payload
    path = v17_path("/partstudios/d/" + args.document + "/w/" + args.workspace + "/e/" + args.element + "/features")
    return post_json(path, payload, creds)


def update_feature(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids(
        [
            ("document", args.document),
            ("workspace", args.workspace),
            ("element", args.element),
            ("feature", args.feature),
        ]
    )
    if rejected is not None:
        return rejected
    if not args.body_file:
        return setup("update-feature requires --body-file. No request was sent.")
    payload = load_feature_body(args.body_file)
    if isinstance(payload, int):
        return payload
    path = v17_path(
        "/partstudios/d/"
        + args.document
        + "/w/"
        + args.workspace
        + "/e/"
        + args.element
        + "/features/featureid/"
        + args.feature
    )
    return post_json(path, payload, creds)


def safe_filename(path: Path) -> str | None:
    name = path.name
    if not name or any(char in name for char in '"\r\n/\\'):
        return None
    if not all(char.isprintable() for char in name):
        return None
    return name


def safe_mime(value: str) -> bool:
    if not value or len(value) > 128 or "/" not in value:
        return False
    left, right = value.split("/", 1)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.+-")
    return bool(left) and bool(right) and all(char in allowed for char in left + right)


def read_import(path: str) -> tuple[Path, bytes] | int:
    file_path = Path(path)
    if not file_path.is_file():
        return setup("import file must be an existing file. No request was sent.")
    if file_path.stat().st_size > IMPORT_LIMIT:
        return setup("import file is larger than 32 MiB. No request was sent.")
    try:
        return file_path, file_path.read_bytes()
    except OSError:
        return setup("import file could not be read. No request was sent.")


def multipart_body(fields: list[tuple[str, str]], filename: str, mime: str, file_bytes: bytes, boundary: str) -> bytes:
    marker = boundary.encode("ascii")
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            b"--"
            + marker
            + b'\r\nContent-Disposition: form-data; name="'
            + name.encode("utf-8")
            + b'"\r\n\r\n'
            + value.encode("utf-8")
            + b"\r\n"
        )
    chunks.append(
        b"--"
        + marker
        + b'\r\nContent-Disposition: form-data; name="file"; filename="'
        + filename.encode("utf-8")
        + b'"\r\nContent-Type: '
        + mime.encode("ascii")
        + b"\r\n\r\n"
        + file_bytes
        + b"\r\n--"
        + marker
        + b"--"
    )
    return b"".join(chunks)


def post_multipart(path: str, body: bytes, boundary: str, creds: tuple[str, str, str]) -> int:
    access_key, secret_key, base_url = creds
    content_type = 'multipart/form-data; boundary="' + boundary + '"'
    result = request_exchange(
        "POST",
        base_url,
        path,
        "",
        body,
        access_key,
        secret_key,
        "application/json",
        content_type,
    )
    if isinstance(result, int):
        return result
    return write_body(result[0])


def import_file(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace)])
    if rejected is not None:
        return rejected
    if not args.file or not args.mime:
        return setup("import-file requires --file and --mime. No request was sent.")
    if not safe_mime(args.mime):
        return setup("mime must be a type/subtype token. No request was sent.")
    if args.format is not None and not plain_name(args.format):
        return setup("formatName must be 1-256 printable characters. No request was sent.")
    loaded = read_import(args.file)
    if isinstance(loaded, int):
        return loaded
    file_path, file_bytes = loaded
    filename = safe_filename(file_path)
    if filename is None:
        return setup("import filename cannot contain quotes or path separators. No request was sent.")
    fields = [("encodedFilename", filename)]
    if args.format:
        fields.append(("formatName", args.format))
    boundary = "onshape" + "".join(secrets.choice(NONCE_ALPHABET) for _ in range(16))
    if boundary.encode("ascii") in file_bytes:
        return setup("import boundary collided with file bytes. No request was sent.")
    path = v17_path("/translations/d/" + args.document + "/w/" + args.workspace)
    return post_multipart(path, multipart_body(fields, filename, args.mime, file_bytes, boundary), boundary, creds)


def upload_blob(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace)])
    if rejected is not None:
        return rejected
    if not args.file or not args.mime:
        return setup("upload-blob requires --file and --mime. No request was sent.")
    if not safe_mime(args.mime):
        return setup("mime must be a type/subtype token. No request was sent.")
    loaded = read_import(args.file)
    if isinstance(loaded, int):
        return loaded
    file_path, file_bytes = loaded
    filename = safe_filename(file_path)
    if filename is None:
        return setup("upload filename cannot contain quotes or path separators. No request was sent.")
    fields = [("encodedFilename", filename), ("fileContentLength", str(len(file_bytes)))]
    boundary = "onshape" + "".join(secrets.choice(NONCE_ALPHABET) for _ in range(16))
    if boundary.encode("ascii") in file_bytes:
        return setup("upload boundary collided with file bytes. No request was sent.")
    path = "/api/blobelements/d/" + args.document + "/w/" + args.workspace
    return post_multipart(path, multipart_body(fields, filename, args.mime, file_bytes, boundary), boundary, creds)


def export_translation(args: argparse.Namespace, creds: tuple[str, str, str]) -> int:
    rejected = require_ids([("document", args.document), ("workspace", args.workspace), ("element", args.element)])
    if rejected is not None:
        return rejected
    if not plain_name(args.format or ""):
        return setup("export-translation requires --format for the official formatName field. No request was sent.")
    path = v17_path(
        "/partstudios/d/" + args.document + "/w/" + args.workspace + "/e/" + args.element + "/translations"
    )
    return post_json(path, {"formatName": args.format}, creds)


def specify_delete(args: argparse.Namespace) -> int:
    if not args.document or not valid_id(args.document):
        return setup("specify-delete requires an explicit alphanumeric --document. No request was sent.")
    if bool(args.workspace) != bool(args.element):
        return setup("element delete requires both --workspace and --element. No request was sent.")
    if args.workspace and (not valid_id(args.workspace) or not valid_id(args.element)):
        return setup("workspace and element must be explicit alphanumeric ids. No request was sent.")
    if args.workspace:
        path = v17_path("/elements/d/" + args.document + "/w/" + args.workspace + "/e/" + args.element)
        target = "element"
    else:
        path = v17_path("/documents/" + args.document)
        target = "document"
    report = {
        "operation": "specify-delete",
        "sent": False,
        "deleted": False,
        "target": target,
        "document": args.document,
        "workspace": args.workspace,
        "element": args.element,
        "officialMethod": "DELETE",
        "officialPath": path,
        "reason": "Delete is specification only. No Onshape request was sent and no user resource was deleted.",
    }
    return write_body((json.dumps(report, ensure_ascii=False) + "\n").encode("utf-8"))


def add_target_args(parser: argparse.ArgumentParser, version_flags: bool) -> None:
    parser.add_argument("--document", "-d")
    parser.add_argument("--workspace", "-w")
    parser.add_argument("--element", "-e")
    if version_flags:
        parser.add_argument("--version", "-v")
        parser.add_argument("--microversion", "-m")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="launch.py")
    sub = parser.add_subparsers(dest="command", required=True)
    docs = sub.add_parser("documents")
    for name in QUERY_PARAMS:
        docs.add_argument("--" + name)
    add_target_args(sub.add_parser("mass-by-material"), True)
    add_target_args(sub.add_parser("export-stl"), False)
    created = sub.add_parser("create-document")
    created.add_argument("--name")
    created.add_argument("--public", action="store_true")
    created.add_argument("--owner-type", type=int)
    studio = sub.add_parser("create-part-studio")
    add_target_args(studio, False)
    studio.add_argument("--name")
    assembly = sub.add_parser("create-assembly")
    add_target_args(assembly, False)
    assembly.add_argument("--name")
    add_target_args(sub.add_parser("get-features"), True)
    add_feature_parser = sub.add_parser("add-feature")
    add_target_args(add_feature_parser, False)
    add_feature_parser.add_argument("--body-file")
    update = sub.add_parser("update-feature")
    add_target_args(update, False)
    update.add_argument("--feature")
    update.add_argument("--body-file")
    imported = sub.add_parser("import-file")
    add_target_args(imported, False)
    imported.add_argument("--file")
    imported.add_argument("--mime")
    imported.add_argument("--format")
    blob = sub.add_parser("upload-blob")
    add_target_args(blob, False)
    blob.add_argument("--file")
    blob.add_argument("--mime")
    exported = sub.add_parser("export-translation")
    add_target_args(exported, False)
    exported.add_argument("--format")
    add_target_args(sub.add_parser("specify-delete"), False)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        code = exc.code
        if code not in {0, None}:
            print(
                "setup_required: unknown command. Delete is not sent; use specify-delete to name an explicit object. "
                "No request was sent.",
                file=sys.stderr,
            )
            return 2
        return 0
    if args.command not in IMPLEMENTED:
        return setup("that command is not implemented. No request was sent.")
    if args.command == "specify-delete":
        return specify_delete(args)
    creds = credentials()
    if isinstance(creds, int):
        return creds
    if args.command == "documents":
        values = {name: getattr(args, name) for name in QUERY_PARAMS if getattr(args, name) is not None}
        return documents(values, creds)
    if args.command == "mass-by-material":
        return mass_by_material(args, creds)
    if args.command == "export-stl":
        return export_stl(args, creds)
    if args.command == "create-document":
        return create_document(args, creds)
    if args.command == "create-part-studio":
        return create_part_studio(args, creds)
    if args.command == "create-assembly":
        return create_assembly(args, creds)
    if args.command == "get-features":
        return get_features(args, creds)
    if args.command == "add-feature":
        return add_feature(args, creds)
    if args.command == "update-feature":
        return update_feature(args, creds)
    if args.command == "import-file":
        return import_file(args, creds)
    if args.command == "upload-blob":
        return upload_blob(args, creds)
    return export_translation(args, creds)


if __name__ == "__main__":
    raise SystemExit(main())
