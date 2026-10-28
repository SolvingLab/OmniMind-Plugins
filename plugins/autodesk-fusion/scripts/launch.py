"""Call the pinned Autodesk Fusion community MCP on loopback.

The server is frankhommers/autodesk-fusion-mcp v1.6.0
(commit cbd01e540af425a81913d4e6c0d49e09e723aeb6). It runs inside
Autodesk Fusion as an add-in and binds 127.0.0.1. This file is a client.
It does not install Fusion, does not copy the add-in, and does not write
%APPDATA%.

Exit codes:
  0  server answered the requested read, or a write the operator allowed
  1  server answered with a tool error or JSON-RPC error
  2  setup_required or refused before any socket
  3  unavailable, identity mismatch, or protocol failure
"""

from __future__ import annotations

import argparse
import json
import sys
from http.client import HTTPConnection, HTTPException
from urllib.parse import urlsplit

PINNED_REPO = "frankhommers/autodesk-fusion-mcp"
PINNED_COMMIT = "cbd01e540af425a81913d4e6c0d49e09e723aeb6"
PINNED_VERSION = "1.6.0"
SERVER_NAME = "autodesk-fusion-mcp"
PROTOCOL = "2026-07-28"
MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT = "io.modelcontextprotocol/clientInfo"
META_SERVER = "io.modelcontextprotocol/serverInfo"
CLIENT_INFO = {"name": "omnimind-autodesk-fusion", "version": "1.6.0"}

PINNED_TOOLS = (
    "call_autodesk_api",
    "execute_python",
    "capture_viewport",
    "get_viewport",
    "set_viewport",
    "fetch_api_documentation",
    "fetch_online_documentation",
    "fetch_design_guide",
    "save_script",
    "load_script",
    "list_scripts",
    "delete_script",
    "get_active_selection",
    "manage_annotations",
)

# Tools whose pinned descriptions read state or bundled text. Everything else
# can change the Fusion session, viewport, scripts, or design.
READ_TOOLS = frozenset(
    {
        "get_viewport",
        "fetch_api_documentation",
        "fetch_online_documentation",
        "fetch_design_guide",
        "list_scripts",
        "load_script",
        "get_active_selection",
    }
)


class ClientError(Exception):
    def __init__(self, status: str, message: str, exit_code: int):
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code


def endpoint_from_url(url: str) -> tuple[str, int]:
    """Accept only the pinned loopback /mcp URL. No socket."""
    text = (url or "").strip()
    if not text:
        raise ClientError(
            "setup_required",
            "FUSION_MCP_URL is required and has no default.",
            2,
        )
    parts = urlsplit(text)
    if parts.scheme != "http":
        raise ClientError(
            "setup_required",
            "Only http://127.0.0.1:<port>/mcp or http://localhost:<port>/mcp is accepted.",
            2,
        )
    if parts.username is not None or parts.password is not None:
        raise ClientError("setup_required", "URL userinfo is not accepted.", 2)
    if parts.query or parts.fragment:
        raise ClientError("setup_required", "URL query and fragment are not accepted.", 2)
    host = parts.hostname
    if host not in ("127.0.0.1", "localhost"):
        raise ClientError(
            "setup_required",
            "Host must be 127.0.0.1 or localhost. The pinned add-in does not serve remote clients.",
            2,
        )
    if parts.port is None:
        raise ClientError(
            "setup_required",
            "Port is required. The pinned add-in default is 8765 and is not assumed.",
            2,
        )
    if parts.path != MCP_PATH:
        raise ClientError("setup_required", "Path must be /mcp.", 2)
    return host, parts.port


def dial_host(host: str) -> str:
    # The add-in binds 127.0.0.1. localhost on Windows can resolve to ::1.
    return "127.0.0.1" if host == "localhost" else host


def tool_needs_write_flag(name: str, arguments: dict) -> bool:
    if name not in PINNED_TOOLS:
        raise ClientError(
            "setup_required",
            f"Unknown tool {name!r}. Only the 14 pinned v1.6.0 tools are called.",
            2,
        )
    if name == "manage_annotations":
        action = arguments.get("action")
        if action == "list":
            return False
        if action in ("claim", "complete", "release"):
            return True
        raise ClientError(
            "setup_required",
            "manage_annotations requires action list, claim, complete, or release.",
            2,
        )
    return name not in READ_TOOLS


def _meta() -> dict:
    return {
        META_VERSION: PROTOCOL,
        META_CAPABILITIES: {},
        META_CLIENT: dict(CLIENT_INFO),
    }


def _request(host: str, port: int, method: str, path: str, body: bytes | None, headers: dict[str, str], timeout: float):
    connection = HTTPConnection(dial_host(host), port, timeout=timeout)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        status = response.status
        content_type = response.getheader("Content-Type", "")
        location = response.getheader("Location")
    except (OSError, HTTPException, TimeoutError) as exc:
        raise ClientError("unavailable", f"No pinned Fusion MCP listener: {exc.__class__.__name__}", 3) from exc
    finally:
        connection.close()
    if 300 <= status < 400:
        raise ClientError(
            "unavailable",
            "Redirect was not followed.",
            3,
        )
    return status, content_type, payload, location


def _json_body(payload: bytes) -> dict:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClientError("unavailable", "Response was not JSON.", 3) from exc
    if not isinstance(value, dict):
        raise ClientError("unavailable", "Response JSON was not an object.", 3)
    return value


def read_health(host: str, port: int, timeout: float) -> dict:
    status, content_type, payload, _location = _request(
        host,
        port,
        "GET",
        HEALTH_PATH,
        None,
        {"Accept": "application/json", "Connection": "close"},
        timeout,
    )
    if status != 200 or "application/json" not in content_type.lower():
        raise ClientError("unavailable", f"GET /health returned HTTP {status}.", 3)
    health = _json_body(payload)
    if health.get("status") != "ok" or health.get("server") != SERVER_NAME:
        raise ClientError(
            "identity_mismatch",
            "Listener is not autodesk-fusion-mcp.",
            3,
        )
    if health.get("version") != PINNED_VERSION:
        raise ClientError(
            "version_mismatch",
            f"Listener version is {health.get('version')!r}, pinned version is {PINNED_VERSION}.",
            3,
        )
    commit = health.get("git_commit")
    if isinstance(commit, str) and commit and not PINNED_COMMIT.startswith(commit) and commit != PINNED_COMMIT:
        raise ClientError(
            "version_mismatch",
            "Listener git_commit does not match the pinned commit.",
            3,
        )
    return health


def mcp_post(host: str, port: int, message: dict, timeout: float) -> dict:
    method = message["method"]
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL,
        "Mcp-Method": method,
        "Connection": "close",
    }
    if method in ("tools/call", "resources/read", "prompts/get"):
        key = "uri" if method == "resources/read" else "name"
        headers["Mcp-Name"] = message["params"][key]
    status, content_type, payload, _location = _request(host, port, "POST", MCP_PATH, body, headers, timeout)
    if status != 200:
        raise ClientError("unavailable", f"POST /mcp returned HTTP {status}.", 3)
    media = content_type.split(";", 1)[0].strip().lower()
    if media == "application/json":
        parsed = _json_body(payload)
    elif media == "text/event-stream":
        parsed = _sse_message(payload, message["id"])
    else:
        raise ClientError("unavailable", f"Unexpected content type {content_type!r}.", 3)
    if parsed.get("jsonrpc") != "2.0" or parsed.get("id") != message["id"]:
        raise ClientError("unavailable", "JSON-RPC id or version did not match.", 3)
    if "error" in parsed:
        raise ClientError("tool_error", json.dumps(parsed["error"], ensure_ascii=True), 1)
    result = parsed.get("result")
    if not isinstance(result, dict):
        raise ClientError("unavailable", "JSON-RPC result was not an object.", 3)
    if result.get("resultType") != "complete":
        raise ClientError("unavailable", "Modern resultType was not complete.", 3)
    server_info = result.get("_meta", {}).get(META_SERVER, {})
    if not isinstance(server_info, dict) or server_info.get("name") != SERVER_NAME:
        raise ClientError("identity_mismatch", "MCP serverInfo name did not match.", 3)
    if server_info.get("version") != PINNED_VERSION:
        raise ClientError("version_mismatch", "MCP serverInfo version did not match.", 3)
    return result


def _sse_message(payload: bytes, request_id) -> dict:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise ClientError("unavailable", "SSE body was not UTF-8.", 3) from exc
    found = None
    for block in text.split("\n\n"):
        data_lines = []
        for line in block.splitlines():
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            value = json.loads("\n".join(data_lines))
        except json.JSONDecodeError as exc:
            raise ClientError("unavailable", "SSE data was not JSON.", 3) from exc
        if isinstance(value, dict) and value.get("id") == request_id:
            found = value
    if found is None:
        raise ClientError("unavailable", "SSE stream had no matching JSON-RPC message.", 3)
    return found


def list_tools(host: str, port: int, timeout: float) -> list[str]:
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {"_meta": _meta()},
    }
    result = mcp_post(host, port, message, timeout)
    tools = result.get("tools")
    if not isinstance(tools, list):
        raise ClientError("unavailable", "tools/list did not return a list.", 3)
    names = []
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise ClientError("unavailable", "tools/list entry had no name.", 3)
        names.append(tool["name"])
    return names


def probe(url: str, timeout: float = 5.0) -> dict:
    host, port = endpoint_from_url(url)
    health = read_health(host, port, timeout)
    names = list_tools(host, port, timeout)
    missing = [name for name in PINNED_TOOLS if name not in names]
    commit = health.get("git_commit")
    return {
        "status": "ok" if not missing else "partial",
        "connected": True,
        "cadWriteSent": False,
        "fusionHostProven": False,
        "endpoint": f"http://{host}:{port}{MCP_PATH}",
        "dialHost": dial_host(host),
        "health": {
            "server": health.get("server"),
            "version": health.get("version"),
            "protocol": health.get("protocol"),
            "git_commit": commit if isinstance(commit, str) else None,
        },
        "commitVerified": commit == PINNED_COMMIT or (
            isinstance(commit, str) and bool(commit) and PINNED_COMMIT.startswith(commit)
        ),
        "toolNames": names,
        "pinnedToolsMissing": missing,
        "addinSurfaceListed": not missing,
    }


def call_tool(url: str, name: str, arguments: dict, allow_cad_write: bool, timeout: float = 30.0) -> dict:
    if not isinstance(arguments, dict):
        raise ClientError("setup_required", "Tool arguments must be a JSON object.", 2)
    if tool_needs_write_flag(name, arguments) and not allow_cad_write:
        raise ClientError(
            "refused_write",
            "This tool can change Fusion. Pass --allow-cad-write to send it. Nothing was sent.",
            2,
        )
    host, port = endpoint_from_url(url)
    health = read_health(host, port, min(timeout, 5.0))
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments, "_meta": _meta()},
    }
    result = mcp_post(host, port, message, timeout)
    wrote = tool_needs_write_flag(name, arguments)
    content = result.get("content")
    is_error = result.get("isError") is True
    return {
        "status": "tool_error" if is_error else "ok",
        "connected": True,
        "cadWriteSent": wrote and not is_error,
        "fusionHostProven": False,
        "tool": name,
        "isError": is_error,
        "content": content if isinstance(content, list) else None,
        "health": {"server": health.get("server"), "version": health.get("version")},
    }


def _emit(payload: dict, code: int) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    if code != 0:
        sys.stderr.write(payload.get("status", "error") + "\n")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call the pinned local Autodesk Fusion community MCP.")
    parser.add_argument("--url", default="")
    sub = parser.add_subparsers(dest="command", required=True)
    probe_cmd = sub.add_parser("probe")
    probe_cmd.add_argument("--timeout", type=float, default=5.0)
    call_cmd = sub.add_parser("call")
    call_cmd.add_argument("tool")
    call_cmd.add_argument("--args", default="{}")
    call_cmd.add_argument("--allow-cad-write", action="store_true")
    call_cmd.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    url = args.url or _env_url()
    try:
        if args.command == "probe":
            payload = probe(url, timeout=args.timeout)
            return _emit(payload, 0 if payload["status"] in ("ok", "partial") else 3)
        try:
            arguments = json.loads(args.args)
        except json.JSONDecodeError as exc:
            raise ClientError("setup_required", "Tool arguments were not JSON.", 2) from exc
        payload = call_tool(
            url,
            args.tool,
            arguments,
            allow_cad_write=args.allow_cad_write,
            timeout=args.timeout,
        )
        return _emit(payload, 1 if payload["status"] == "tool_error" else 0)
    except ClientError as exc:
        return _emit(
            {
                "status": exc.status,
                "connected": False,
                "cadWriteSent": False,
                "fusionHostProven": False,
                "message": str(exc),
            },
            exc.exit_code,
        )


def _env_url() -> str:
    import os

    return os.environ.get("FUSION_MCP_URL", "")


if __name__ == "__main__":
    sys.exit(main())
