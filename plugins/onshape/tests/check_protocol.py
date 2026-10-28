"""Adapter protocol check. Not a live Onshape session and not a CAD write."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "scripts" / "launch.py"
sys.path.insert(0, str(LAUNCH.parent))
import launch  # noqa: E402

ACCESS = "synthetic-access-key"
SECRET = "synthetic-secret-not-live"
SEEN: list[dict[str, str]] = []
MODE = {"name": "documents"}


class Handler(BaseHTTPRequestHandler):
    def record(self):
        parsed = urlsplit(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        SEEN.append(
            {
                "method": self.command,
                "path": parsed.path,
                "query": parsed.query,
                "authorization": self.headers.get("Authorization", ""),
                "date": self.headers.get("Date", ""),
                "nonce": self.headers.get("On-Nonce", ""),
                "content_type": self.headers.get("Content-Type", ""),
                "accept": self.headers.get("Accept", ""),
                "body": body.decode("utf-8", "replace"),
            }
        )
        return parsed

    def do_GET(self):
        parsed = self.record()
        if MODE["name"] == "documents-307" and parsed.path == "/api/documents":
            self.send_response(307)
            self.send_header("Location", "http://evil.example/api/documents")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if parsed.path == "/api/documents":
            body = b'{"items":[]}\n'
        elif parsed.path.startswith("/api/parts/"):
            body = json.dumps(
                [
                    {"partId": "P1", "material": {"id": "mat-steel"}},
                    {"partId": "P2", "material": {"id": "mat-steel"}},
                    {"partId": "P3"},
                ]
            ).encode("utf-8")
        elif parsed.path.endswith("/massproperties"):
            body = json.dumps(
                {
                    "bodies": {
                        "P1": {"hasMass": True, "mass": [2.5]},
                        "P2": {"hasMass": False, "mass": [9]},
                        "P3": {"hasMass": True, "mass": [1]},
                    }
                }
            ).encode("utf-8")
        elif parsed.path.endswith("/stl") and MODE["name"] == "stl-foreign":
            self.send_response(307)
            self.send_header("Location", "http://evil.example/stl-body")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        elif parsed.path.endswith("/stl"):
            host, port = self.server.server_address[:2]
            location = "http://" + host + ":" + str(port) + "/stl-body?mode=text"
            self.send_response(307)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        elif parsed.path == "/stl-body":
            body = b"solid fixture\n"
        elif parsed.path.endswith("/features"):
            body = b'{"features":[]}\n'
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = self.record()
        if parsed.path.startswith("/api/v17/") or parsed.path.startswith("/api/blobelements/"):
            body = b'{"id":"created"}\n'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        self.record()
        self.send_response(500)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        return


def run_launcher(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(LAUNCH), *args],
        check=False,
        capture_output=True,
        env=env,
    )


def signed_ok(item: dict[str, str], path: str, query: str, method: str = "GET") -> bool:
    signed = (
        method
        + "\n"
        + item["nonce"]
        + "\n"
        + item["date"]
        + "\n"
        + item["content_type"]
        + "\n"
        + path
        + "\n"
        + query
        + "\n"
    ).lower()
    digest = hmac.new(SECRET.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).digest()
    expected = "On " + ACCESS + ":HmacSHA256:" + base64.b64encode(digest).decode("ascii")
    return (
        item["authorization"] == expected
        and item["path"] == path
        and item["query"] == query
        and item.get("method") == method
    )


def leaked(completed: subprocess.CompletedProcess[bytes]) -> bool:
    text = completed.stdout + b"\n" + completed.stderr
    return SECRET.encode("utf-8") in text or ACCESS.encode("utf-8") in text


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    results = []
    env = os.environ.copy()
    for key in ("ONSHAPE_ACCESS_KEY", "ONSHAPE_SECRET_KEY", "ONSHAPE_BASE_URL"):
        env.pop(key, None)
    env.update(
        {
            "ONSHAPE_ACCESS_KEY": ACCESS,
            "ONSHAPE_SECRET_KEY": SECRET,
            "ONSHAPE_BASE_URL": base,
        }
    )
    try:
        node_signature = None
        node_script = (
            'const crypto=require("crypto"); const qs=require("querystring");'
            'const str="GET\\nABCDEFGHIJKLMNOPQRSTUVWXY\\nMon, 11 Apr 2016 20:08:56 GMT\\n'
            'application/json\\n/api/documents\\nlimit=1\\n".toLowerCase();'
            'const hmac=crypto.createHmac("sha256","synthetic-secret-not-live").update(str).digest("base64");'
            'process.stdout.write(hmac+"\\n"+qs.stringify({query:"a b",limit:"1"})+"\\n"+qs.stringify({massAsGroup:false}));'
        )
        probe = subprocess.run(
            ["node", "-e", node_script],
            check=False,
            capture_output=True,
        )
        if probe.returncode == 0:
            hmac_line, query_line, mass_line = probe.stdout.decode("utf-8").splitlines()
            headers = launch.authorization(
                "GET",
                "/api/documents",
                "limit=1",
                ACCESS,
                SECRET,
                nonce="ABCDEFGHIJKLMNOPQRSTUVWXY",
                stamp="Mon, 11 Apr 2016 20:08:56 GMT",
            )
            node_signature = headers["Authorization"].endswith(hmac_line) and query_line == launch.query_string(
                {"query": "a b", "limit": "1"}, launch.QUERY_PARAMS
            ) and mass_line == "massAsGroup=false"
        results.append(
            {
                "name": "signature-matches-node-crypto",
                "ok": node_signature is True,
                "matched": node_signature,
            }
        )
        results.append(
            {
                "name": "pinned-paths",
                "ok": launch.build_dwmve_path("parts", "DOC", "w", "WS", "EL")
                == "/api/parts/d/DOC/w/WS/e/EL"
                and launch.build_dwmve_path("partstudios", "DOC", "v", "VER", "EL", "massproperties")
                == "/api/partstudios/d/DOC/v/VER/e/EL/massproperties"
                and launch.build_dwmve_path("partstudios", "DOC", "w", "WS", "EL", "stl")
                == "/api/partstudios/d/DOC/w/WS/e/EL/stl",
            }
        )
        results.append(
            {
                "name": "redirect-host-family",
                "ok": launch.host_allowed("https://cad.onshape.com", "https://blob.onshape.com/x")
                and not launch.host_allowed("https://cad.onshape.com", "https://evil.example/x")
                and not launch.host_allowed("https://cad.onshape.com", "https://blob.onshape.com.evil.example/x")
                and not launch.host_allowed(base, "http://evil.example/x"),
            }
        )

        missing = os.environ.copy()
        for key in ("ONSHAPE_ACCESS_KEY", "ONSHAPE_SECRET_KEY", "ONSHAPE_BASE_URL"):
            missing.pop(key, None)
        before = len(SEEN)
        completed = run_launcher(["documents", "--limit", "1"], missing)
        results.append(
            {
                "name": "missing-credentials-no-request",
                "ok": completed.returncode == 2
                and len(SEEN) == before
                and b"setup_required" in completed.stderr
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        MODE["name"] = "documents"
        before = len(SEEN)
        completed = run_launcher(["documents", "--limit", "1", "--query", "a b"], env)
        seen = SEEN[before:]
        results.append(
            {
                "name": "documents-query-signed-against-local-fixture",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/documents", launch.query_string({"query": "a b", "limit": "1"}, launch.QUERY_PARAMS))
                and seen[0]["accept"] == "application/vnd.onshape.v1+json"
                and completed.stdout.strip() == b'{"items":[]}'
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(seen),
            }
        )

        MODE["name"] = "documents-307"
        before = len(SEEN)
        completed = run_launcher(["documents"], env)
        results.append(
            {
                "name": "documents-307-not-followed",
                "ok": completed.returncode == 1 and len(SEEN) == before + 1 and b"http_status: 307" in completed.stderr,
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        MODE["name"] = "mass"
        before = len(SEEN)
        completed = run_launcher(
            ["mass-by-material", "--document", "DOC", "--workspace", "WS", "--element", "EL"],
            env,
        )
        seen = SEEN[before:]
        tally_ok = False
        try:
            tally_ok = json.loads(completed.stdout.decode("utf-8")) == {
                "operation": "mass-by-material",
                "massesByMaterial": {"mat-steel": 2.5},
                "totalMass": 2.5,
            }
        except json.JSONDecodeError:
            tally_ok = False
        results.append(
            {
                "name": "mass-by-material-two-signed-reads",
                "ok": completed.returncode == 0
                and len(seen) == 2
                and signed_ok(seen[0], "/api/parts/d/DOC/w/WS/e/EL", "")
                and signed_ok(seen[1], "/api/partstudios/d/DOC/w/WS/e/EL/massproperties", "massAsGroup=false")
                and tally_ok
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(seen),
                "stdout": completed.stdout.decode("utf-8", "replace").strip(),
            }
        )

        before = len(SEEN)
        completed = run_launcher(["mass-by-material", "--document", "DOC", "--element", "EL"], env)
        results.append(
            {
                "name": "mass-missing-version-context-no-request",
                "ok": completed.returncode == 2 and len(SEEN) == before and b"setup_required" in completed.stderr,
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        MODE["name"] = "stl"
        before = len(SEEN)
        completed = run_launcher(
            ["export-stl", "--document", "DOC", "--workspace", "WS", "--element", "EL"],
            env,
        )
        seen = SEEN[before:]
        results.append(
            {
                "name": "export-stl-resigns-same-host-307",
                "ok": completed.returncode == 0
                and len(seen) == 2
                and signed_ok(seen[0], "/api/partstudios/d/DOC/w/WS/e/EL/stl", "")
                and seen[0]["accept"] == "application/vnd.onshape.v1+octet-stream"
                and signed_ok(seen[1], "/stl-body", "mode=text")
                and seen[0]["authorization"] != seen[1]["authorization"]
                and completed.stdout == b"solid fixture\n"
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(seen),
            }
        )

        MODE["name"] = "stl-foreign"
        before = len(SEEN)
        completed = run_launcher(
            ["export-stl", "--document", "DOC", "--workspace", "WS", "--element", "EL"],
            env,
        )
        results.append(
            {
                "name": "export-stl-foreign-307-not-followed",
                "ok": completed.returncode == 1
                and len(SEEN) == before + 1
                and b"redirect_not_followed" in completed.stderr
                and b"evil.example" in completed.stderr
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        before = len(SEEN)
        completed = run_launcher(["create-document", "--name", "Bracket"], env)
        seen = SEEN[before:]
        results.append(
            {
                "name": "create-document-signed-post",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/v17/documents", "", "POST")
                and seen[0]["body"] == '{"name":"Bracket","isPublic":false}'
                and seen[0]["content_type"] == "application/json"
                and not leaked(completed),
                "actualCode": completed.returncode,
                "requests": len(seen),
                "body": seen[0]["body"] if seen else "",
            }
        )

        before = len(SEEN)
        completed = run_launcher(["create-document"], env)
        results.append(
            {
                "name": "create-document-missing-name-no-request",
                "ok": completed.returncode == 2 and len(SEEN) == before,
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        before = len(SEEN)
        completed = run_launcher(
            ["create-part-studio", "--document", "DOC", "--workspace", "WS", "--name", "Studio"],
            env,
        )
        seen = SEEN[before:]
        results.append(
            {
                "name": "create-part-studio-signed-post",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/v17/partstudios/d/DOC/w/WS", "", "POST")
                and seen[0]["body"] == '{"name":"Studio"}'
                and not leaked(completed),
                "actualCode": completed.returncode,
            }
        )

        before = len(SEEN)
        completed = run_launcher(
            ["create-assembly", "--document", "DOC", "--workspace", "WS", "--name", "Asm"],
            env,
        )
        seen = SEEN[before:]
        results.append(
            {
                "name": "create-assembly-signed-post",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/v17/assemblies/d/DOC/w/WS", "", "POST")
                and seen[0]["body"] == '{"name":"Asm"}',
                "actualCode": completed.returncode,
            }
        )

        before = len(SEEN)
        completed = run_launcher(
            ["get-features", "--document", "DOC", "--workspace", "WS", "--element", "EL"],
            env,
        )
        seen = SEEN[before:]
        results.append(
            {
                "name": "get-features-signed-get",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/v17/partstudios/d/DOC/w/WS/e/EL/features", "", "GET")
                and seen[0]["accept"] == "application/json",
                "actualCode": completed.returncode,
                "stderr": completed.stderr.decode("utf-8", "replace"),
            }
        )

        import tempfile

        feature = {"feature": {"featureType": "extrude", "name": "Extrude 1", "parameters": []}}
        with tempfile.TemporaryDirectory() as tmp:
            body_path = str(Path(tmp) / "feature.json")
            Path(body_path).write_text(json.dumps(feature), encoding="utf-8")
            before = len(SEEN)
            completed = run_launcher(
                ["add-feature", "--document", "DOC", "--workspace", "WS", "--element", "EL", "--body-file", body_path],
                env,
            )
            seen = SEEN[before:]
            sent = json.loads(seen[0]["body"]) if seen else None
            results.append(
                {
                    "name": "add-feature-posts-explicit-body",
                    "ok": completed.returncode == 0
                    and len(seen) == 1
                    and signed_ok(seen[0], "/api/v17/partstudios/d/DOC/w/WS/e/EL/features", "", "POST")
                    and sent == feature
                    and not leaked(completed),
                    "actualCode": completed.returncode,
                }
            )
            before = len(SEEN)
            completed = run_launcher(
                [
                    "update-feature",
                    "--document",
                    "DOC",
                    "--workspace",
                    "WS",
                    "--element",
                    "EL",
                    "--feature", "FID",
                    "--body-file",
                    body_path,
                ],
                env,
            )
            seen = SEEN[before:]
            results.append(
                {
                    "name": "update-feature-explicit-id",
                    "ok": completed.returncode == 0
                    and len(seen) == 1
                    and signed_ok(
                        seen[0],
                        "/api/v17/partstudios/d/DOC/w/WS/e/EL/features/featureid/FID",
                        "",
                        "POST",
                    ),
                    "actualCode": completed.returncode,
                }
            )
            import_path = str(Path(tmp) / "bracket.step")
            Path(import_path).write_bytes(b"ISO-10303-21;\n")
            before = len(SEEN)
            completed = run_launcher(
                [
                    "import-file",
                    "--document",
                    "DOC",
                    "--workspace",
                    "WS",
                    "--file",
                    import_path,
                    "--mime",
                    "application/step",
                    "--format",
                    "STEP",
                ],
                env,
            )
            seen = SEEN[before:]
            results.append(
                {
                    "name": "import-file-signed-translation",
                    "ok": completed.returncode == 0
                    and len(seen) == 1
                    and signed_ok(seen[0], "/api/v17/translations/d/DOC/w/WS", "", "POST")
                    and seen[0]["content_type"].startswith("multipart/form-data; boundary=")
                    and "name=\"encodedFilename\"" in seen[0]["body"]
                    and "name=\"formatName\"" in seen[0]["body"]
                    and "ISO-10303-21;" in seen[0]["body"]
                    and not leaked(completed),
                    "actualCode": completed.returncode,
                }
            )
            before = len(SEEN)
            completed = run_launcher(
                [
                    "upload-blob",
                    "--document",
                    "DOC",
                    "--workspace",
                    "WS",
                    "--file",
                    import_path,
                    "--mime",
                    "text/plain",
                ],
                env,
            )
            seen = SEEN[before:]
            results.append(
                {
                    "name": "upload-blob-pinned-path",
                    "ok": completed.returncode == 0
                    and len(seen) == 1
                    and signed_ok(seen[0], "/api/blobelements/d/DOC/w/WS", "", "POST")
                    and "name=\"fileContentLength\"" in seen[0]["body"]
                    and not leaked(completed),
                    "actualCode": completed.returncode,
                }
            )

        before = len(SEEN)
        completed = run_launcher(
            ["export-translation", "--document", "DOC", "--workspace", "WS", "--element", "EL", "--format", "STEP"],
            env,
        )
        seen = SEEN[before:]
        results.append(
            {
                "name": "export-translation-format-name",
                "ok": completed.returncode == 0
                and len(seen) == 1
                and signed_ok(seen[0], "/api/v17/partstudios/d/DOC/w/WS/e/EL/translations", "", "POST")
                and seen[0]["body"] == '{"formatName":"STEP"}',
                "actualCode": completed.returncode,
                "body": seen[0]["body"] if seen else "",
            }
        )

        before = len(SEEN)
        completed = run_launcher(
            ["specify-delete", "--document", "DOC", "--workspace", "WS", "--element", "EL"],
            env,
        )
        specified = {}
        try:
            specified = json.loads(completed.stdout.decode("utf-8"))
        except json.JSONDecodeError:
            specified = {}
        results.append(
            {
                "name": "specify-delete-sends-nothing",
                "ok": completed.returncode == 0
                and len(SEEN) == before
                and specified.get("sent") is False
                and specified.get("deleted") is False
                and specified.get("officialMethod") == "DELETE"
                and specified.get("officialPath") == "/api/v17/elements/d/DOC/w/WS/e/EL"
                and not any(item.get("method") == "DELETE" for item in SEEN),
                "actualCode": completed.returncode,
                "requests": len(SEEN) - before,
            }
        )

        for command in ("new-document", "delete", "delete-element", "expensive-do-nothing"):
            before = len(SEEN)
            completed = run_launcher([command], env)
            results.append(
                {
                    "name": command + "-rejected-no-request",
                    "ok": completed.returncode == 2 and len(SEEN) == before and b"setup_required" in completed.stderr,
                    "actualCode": completed.returncode,
                    "requests": len(SEEN) - before,
                }
            )
    finally:
        server.shutdown()

    report = {
        "label": "adapter protocol check, NOT live Onshape and NOT a CAD write",
        "liveOnshapeCalled": False,
        "cadWriteSent": False,
        "credentials": "synthetic",
        "passed": all(item["ok"] for item in results),
        "checks": results,
    }
    print(json.dumps({"passed": report["passed"], "failed": [item["name"] for item in results if not item["ok"]]}, ensure_ascii=False))
    if not report["passed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
