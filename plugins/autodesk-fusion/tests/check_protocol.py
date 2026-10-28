"""Protocol checks for the Autodesk Fusion community MCP client.

Uses a local fixture that speaks the pinned v1.6.0 subset. It does not start
Autodesk Fusion and does not treat a fixture response as native acceptance.
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import launch  # noqa: E402


PINNED_TOOLS = [
    {
        "name": name,
        "description": name,
        "inputSchema": {"type": "object", "properties": {}},
    }
    for name in launch.PINNED_TOOLS
]


class Fixture(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, mode: str):
        self.mode = mode
        self.requests: list[tuple[str, str, dict, bytes]] = []
        self.lock = threading.Lock()
        super().__init__(("127.0.0.1", 0), _Handler)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/mcp"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._record(b"")
        if self.server.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "http://example.test/health")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path != "/health":
            self._empty(404)
            return
        health = {
            "status": "ok",
            "server": "autodesk-fusion-mcp",
            "version": "1.6.0",
            "git_commit": None,
            "protocol": "2026-07-28",
        }
        if self.server.mode == "other-server":
            health["server"] = "not-fusion"
        elif self.server.mode == "other-version":
            health["version"] = "9.9.9"
        elif self.server.mode == "other-commit":
            health["git_commit"] = "deadbeef"
        self._json(200, health)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self._record(body)
        if self.path != "/mcp":
            self._empty(404)
            return
        message = json.loads(body.decode("utf-8"))
        if self.headers.get("MCP-Protocol-Version") != message["params"]["_meta"][launch.META_VERSION]:
            self._empty(400)
            return
        if self.headers.get("Mcp-Method") != message["method"]:
            self._empty(400)
            return
        if message["method"] == "tools/call" and self.headers.get("Mcp-Name") != message["params"]["name"]:
            self._empty(400)
            return
        if message["method"] == "tools/list":
            tools = PINNED_TOOLS
            if self.server.mode == "partial":
                tools = [PINNED_TOOLS[0]]
            self._json(200, _rpc(message, {"tools": tools}))
            return
        if message["method"] == "tools/call":
            if self.server.mode == "tool-json-error":
                self._json(
                    200,
                    _rpc(
                        message,
                        {"content": [{"type": "text", "text": "fixture tool error"}], "isError": True},
                    ),
                )
                return
            self._sse(_rpc(message, {"content": [{"type": "text", "text": "fixture-read"}], "isError": False}))
            return
        self._empty(404)

    def _record(self, body: bytes) -> None:
        with self.server.lock:
            self.server.requests.append((self.command, self.path, dict(self.headers), body))

    def _empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _sse(self, payload: dict) -> None:
        event = ("event: message\ndata: " + json.dumps(payload) + "\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.wfile.write(f"{len(event):X}\r\n".encode("ascii") + event + b"\r\n")
        self.wfile.write(b"0\r\n\r\n")


def _rpc(message: dict, result: dict) -> dict:
    result = dict(result)
    result["resultType"] = "complete"
    result["_meta"] = {
        launch.META_SERVER: {"name": launch.SERVER_NAME, "version": launch.PINNED_VERSION}
    }
    return {"jsonrpc": "2.0", "id": message["id"], "result": result}


def serve(mode: str):
    server = Fixture(mode)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def fail(name: str, detail: str) -> None:
    raise SystemExit(f"FAIL {name}: {detail}")


def expect_error(name: str, fn, status: str, code: int) -> None:
    try:
        fn()
    except launch.ClientError as exc:
        if exc.status != status or exc.exit_code != code:
            fail(name, f"{exc.status}/{exc.exit_code} != {status}/{code}: {exc}")
        return
    fail(name, "expected ClientError")


def main() -> int:
    checks: list[str] = []

    expect_error("missing-url", lambda: launch.probe(""), "setup_required", 2)
    expect_error(
        "remote-url",
        lambda: launch.probe("http://example.test:8765/mcp"),
        "setup_required",
        2,
    )
    expect_error(
        "https-url",
        lambda: launch.probe("https://127.0.0.1:8765/mcp"),
        "setup_required",
        2,
    )
    expect_error(
        "userinfo-url",
        lambda: launch.probe("http://user:secret@127.0.0.1:8765/mcp"),
        "setup_required",
        2,
    )
    expect_error(
        "query-url",
        lambda: launch.probe("http://127.0.0.1:8765/mcp?x=1"),
        "setup_required",
        2,
    )
    expect_error(
        "wrong-path",
        lambda: launch.probe("http://127.0.0.1:8765/api"),
        "setup_required",
        2,
    )
    expect_error(
        "missing-port",
        lambda: launch.probe("http://127.0.0.1/mcp"),
        "setup_required",
        2,
    )
    expect_error(
        "ipv6-url",
        lambda: launch.probe("http://[::1]:8765/mcp"),
        "setup_required",
        2,
    )
    checks.append("refused-before-connect")

    original = launch.HTTPConnection

    def boom(*_args, **_kwargs):
        raise AssertionError("socket opened")

    launch.HTTPConnection = boom
    try:
        expect_error("write-without-flag", lambda: launch.call_tool(
            "http://127.0.0.1:9/mcp",
            "execute_python",
            {"code": "print(1)", "persistent": False},
            False,
        ), "refused_write", 2)
        expect_error("unknown-tool", lambda: launch.call_tool(
            "http://127.0.0.1:9/mcp",
            "delete_document",
            {},
            True,
        ), "setup_required", 2)
        expect_error("annotation-claim", lambda: launch.call_tool(
            "http://127.0.0.1:9/mcp",
            "manage_annotations",
            {"action": "claim", "id": "a", "revision": 1},
            False,
        ), "refused_write", 2)
        expect_error("bad-args", lambda: launch.call_tool(
            "http://127.0.0.1:9/mcp",
            "get_viewport",
            ["nope"],  # type: ignore[arg-type]
            False,
        ), "setup_required", 2)
    finally:
        launch.HTTPConnection = original
    checks.append("write-and-unknown-no-socket")

    closed = serve("ok")
    try:
        listed = launch.probe(closed.url, timeout=3)
    finally:
        closed.shutdown()
    if listed["status"] != "ok" or listed["cadWriteSent"] or listed["fusionHostProven"]:
        fail("probe-ok", json.dumps(listed))
    if listed["pinnedToolsMissing"] or not listed["addinSurfaceListed"]:
        fail("probe-tools", json.dumps(listed))
    if any(item[0] == "POST" and b"tools/call" in item[3] for item in closed.requests):
        fail("probe-called-tool", "probe sent tools/call")
    if not any(item[0] == "GET" and item[1] == "/health" for item in closed.requests):
        fail("probe-health", "probe skipped /health")
    checks.append("probe-lists-pinned-tools")

    partial = serve("partial")
    try:
        partial_result = launch.probe(partial.url, timeout=3)
    finally:
        partial.shutdown()
    if partial_result["status"] != "partial" or partial_result["addinSurfaceListed"]:
        fail("partial", json.dumps(partial_result))
    checks.append("partial-surface")

    for mode, status in (
        ("other-server", "identity_mismatch"),
        ("other-version", "version_mismatch"),
        ("other-commit", "version_mismatch"),
        ("redirect", "unavailable"),
    ):
        server = serve(mode)
        try:
            expect_error(mode, lambda: launch.probe(server.url, timeout=3), status, 3)
            posts = [item for item in server.requests if item[0] == "POST"]
            if posts:
                fail(mode, "request continued after rejection")
            if mode == "redirect":
                paths = [item[1] for item in server.requests]
                if paths != ["/health"]:
                    fail("redirect-followed", str(paths))
        finally:
            server.shutdown()
    checks.append("identity-version-redirect-stop")

    read_server = serve("ok")
    try:
        called = launch.call_tool(read_server.url, "get_viewport", {}, False, timeout=3)
    finally:
        read_server.shutdown()
    if called["status"] != "ok" or called["cadWriteSent"] or called["content"][0]["text"] != "fixture-read":
        fail("read-call", json.dumps(called))
    post = [item for item in read_server.requests if item[0] == "POST"][-1]
    if post[2].get("Mcp-Method") != "tools/call" or post[2].get("Mcp-Name") != "get_viewport":
        fail("read-headers", str(post[2]))
    checks.append("read-tool-sse")

    list_only = serve("ok")
    try:
        listed_annotations = launch.call_tool(
            list_only.url,
            "manage_annotations",
            {"action": "list"},
            False,
            timeout=3,
        )
    finally:
        list_only.shutdown()
    if listed_annotations["cadWriteSent"]:
        fail("annotation-list", json.dumps(listed_annotations))
    checks.append("annotation-list-is-read")

    error_server = serve("tool-json-error")
    try:
        tool_error = launch.call_tool(error_server.url, "get_viewport", {}, False, timeout=3)
    finally:
        error_server.shutdown()
    if tool_error["status"] != "tool_error" or tool_error["cadWriteSent"]:
        fail("tool-error", json.dumps(tool_error))
    checks.append("json-tool-error")

    code = launch.main(["probe"])
    if code != 2:
        fail("cli-missing", str(code))
    checks.append("cli-missing-url")

    cli_server = serve("ok")
    try:
        code = launch.main(["--url", cli_server.url, "call", "set_viewport", "--args", "{}"])
    finally:
        cli_server.shutdown()
    if code != 2:
        fail("cli-write", str(code))
    if any(item[0] == "POST" for item in cli_server.requests):
        fail("cli-write-sent", "write flag absence still posted")
    checks.append("cli-write-refused")

    print(json.dumps({"passed": True, "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
