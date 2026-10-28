import json
import os
import subprocess
import sys
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import baidu_netdisk as api  # noqa: E402
import netdisk  # noqa: E402


class FakeTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        return self.handler(request)


def json_response(payload, status=200):
    return api.HttpResponse(status, {"Content-Type": "application/json"}, json.dumps(payload).encode("utf-8"))


def query_of(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True))


class AdapterTests(unittest.TestCase):
    def test_status_without_token_does_not_call_network(self):
        transport = FakeTransport(lambda request: (_ for _ in ()).throw(AssertionError("network")))
        result = api.status(api.Config(), transport)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.payload["state"], "unavailable")
        self.assertFalse(result.payload["upstreamCalled"])
        self.assertEqual(result.payload["product"], "百度网盘")
        self.assertEqual(transport.calls, [])

    def test_blank_token_is_missing(self):
        config = api.config_from_env({api.ENV_ACCESS_TOKEN: "   "})
        self.assertFalse(config.access_token)

    def test_status_does_not_echo_token(self):
        token = "token-value-not-for-logs"
        seen = []

        def handler(request):
            seen.append(request.url)
            if "method=uinfo" in request.url:
                return json_response({"errno": 0, "baidu_name": "demo", "netdisk_name": "demo"})
            return json_response({"errno": 0, "total": 1, "used": 0, "free": 1})

        result = api.status(api.Config(access_token=token), FakeTransport(handler))
        text = json.dumps(result.payload, ensure_ascii=False)
        self.assertNotIn(token, text)
        self.assertTrue(result.payload["ok"])
        self.assertTrue(any("method=uinfo" in url for url in seen))
        self.assertTrue(all(request.headers["User-Agent"] == "pan.baidu.com" for request in []))

    def test_list_uses_official_endpoint(self):
        captured = {}

        def handler(request):
            captured["request"] = request
            return json_response({"errno": 0, "list": [{"path": "/apps/demo/a.txt", "isdir": 0}]})

        result = api.list_dir(api.Config(access_token="token-value-ok"), FakeTransport(handler), "/apps/demo", 0, 10, "time", 1)
        request = captured["request"]
        parts = urllib.parse.urlsplit(request.url)
        self.assertEqual(request.method, "GET")
        self.assertEqual(parts.scheme, "https")
        self.assertEqual(parts.netloc, "pan.baidu.com")
        self.assertEqual(parts.path, "/rest/2.0/xpan/file")
        self.assertEqual(request.headers["User-Agent"], "pan.baidu.com")
        params = query_of(request.url)
        self.assertEqual(params["method"], "list")
        self.assertEqual(params["dir"], "/apps/demo")
        self.assertEqual(params["order"], "time")
        self.assertEqual(params["limit"], "10")
        self.assertEqual(result.payload["upstream"]["list"][0]["path"], "/apps/demo/a.txt")

    def test_list_without_token_does_not_invent_files(self):
        result = api.list_dir(api.Config(), FakeTransport(lambda request: json_response({"list": []})), "/", 0, 10, "name", 0)
        self.assertFalse(result.payload["ok"])
        self.assertNotIn("list", result.payload)

    def test_search_rejects_long_key_before_network(self):
        result = api.search(api.Config(access_token="token-value-ok"), FakeTransport(lambda request: json_response({})), "a" * 31, "/", 4, True)
        self.assertEqual(result.exit_code, 2)
        self.assertFalse(result.payload["upstreamCalled"])

    def test_delete_requires_confirmation_and_apps_prefix(self):
        transport = FakeTransport(lambda request: json_response({"errno": 0}))
        config = api.Config(access_token="token-value-ok")
        unconfirmed = api.delete_path(config, transport, "/apps/demo/a.txt", False)
        self.assertEqual(unconfirmed.payload["reason"], "confirmation_required")
        self.assertEqual(transport.calls, [])
        outside = api.delete_path(config, transport, "/docs/a.txt", True)
        self.assertEqual(outside.exit_code, 2)
        self.assertEqual(transport.calls, [])
        confirmed = api.delete_path(config, transport, "/apps/demo/a.txt", True)
        self.assertEqual(confirmed.exit_code, 0)
        request = transport.calls[0]
        self.assertIn("method=filemanager", request.url)
        self.assertIn("opera=delete", request.url)
        body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
        self.assertEqual(json.loads(body["filelist"]), ["/apps/demo/a.txt"])
        self.assertNotIn("ondup", body)

    def test_mkdir_form_matches_official_create(self):
        transport = FakeTransport(lambda request: json_response({"errno": 0, "isdir": 1, "path": "/apps/demo/资料"}))
        result = api.make_dir(api.Config(access_token="token-value-ok", app_dir="/apps/demo"), transport, "/apps/demo/资料", True)
        self.assertTrue(result.payload["ok"])
        request = transport.calls[0]
        params = query_of(request.url)
        body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
        self.assertEqual(params["method"], "create")
        self.assertEqual(body["isdir"], "1")
        self.assertEqual(body["path"], "/apps/demo/资料")
        self.assertEqual(body["rtype"], "0")
        rejected = api.make_dir(api.Config(access_token="token-value-ok", app_dir="/apps/demo"), transport, "/apps/other/资料", True)
        self.assertEqual(rejected.exit_code, 2)

    def test_authorize_url_omits_secret(self):
        config = api.Config(app_key="app-key-value", secret_key="secret-value-hidden", redirect_uri="https://example.invalid/cb")
        result = api.authorize_url(config, "code")
        url = result.payload["url"]
        self.assertIn("response_type=code", url)
        self.assertIn("scope=basic%2Cnetdisk", url)
        self.assertNotIn("secret-value-hidden", url)
        self.assertNotIn("client_secret", url)
        official = api.authorize_url(config, "official-mcp")
        self.assertEqual(official.payload["url"], api.OFFICIAL_MCP_AUTHORIZE_URL)
        self.assertFalse(official.payload["upstreamCalled"])

    def test_quota_and_uinfo_hosts(self):
        urls = []

        def handler(request):
            urls.append(request.url)
            return json_response({"errno": 0})

        config = api.Config(access_token="token-value-ok")
        api.quota(config, FakeTransport(handler))
        api.uinfo(config, FakeTransport(handler))
        quota_parts = urllib.parse.urlsplit(urls[0])
        uinfo_parts = urllib.parse.urlsplit(urls[1])
        self.assertEqual(quota_parts.path, "/api/quota")
        self.assertEqual(uinfo_parts.path, "/rest/2.0/xpan/nas")
        self.assertEqual(query_of(urls[1])["method"], "uinfo")

    def test_nonzero_errno_is_not_success(self):
        result = api.quota(
            api.Config(access_token="token-value-ok"),
            FakeTransport(lambda request: json_response({"errno": -6, "errmsg": "Invalid Bduss"})),
        )
        self.assertFalse(result.payload["ok"])
        self.assertEqual(result.exit_code, 1)

    def test_slice_spans_follow_official_4mb_boundary(self):
        self.assertEqual(api.SLICE_SIZE, 4 * 1024 * 1024)
        self.assertEqual(api.slice_spans(0), [(0, 0)])
        self.assertEqual(api.slice_spans(api.SLICE_SIZE), [(0, api.SLICE_SIZE)])
        self.assertEqual(
            api.slice_spans(api.SLICE_SIZE + 1),
            [(0, api.SLICE_SIZE), (api.SLICE_SIZE, api.SLICE_SIZE + 1)],
        )

    def test_upload_without_token_does_not_slice_or_call_network(self):
        transport = FakeTransport(lambda request: (_ for _ in ()).throw(AssertionError("network")))
        result = api.upload_file(api.Config(), transport, "local.bin", "/apps/demo/local.bin", b"abcdef", True)
        self.assertEqual(result.exit_code, 2)
        self.assertFalse(result.payload["upstreamCalled"])
        self.assertEqual(transport.calls, [])

    def test_upload_single_slice_sequence(self):
        calls = []

        def handler(request):
            calls.append(request)
            params = query_of(request.url)
            if params.get("method") == "precreate":
                return json_response({"errno": 0, "uploadid": "up-1", "block_list": [0]})
            if params.get("method") == "locateupload":
                self.assertEqual(params["appid"], "250528")
                self.assertEqual(params["upload_version"], "2.0")
                return json_response({"error_code": 0, "servers": [{"server": "https://c.pcs.baidu.com"}]})
            if params.get("method") == "upload":
                self.assertEqual(urllib.parse.urlsplit(request.url).netloc, "c.pcs.baidu.com")
                self.assertEqual(params["type"], "tmpfile")
                self.assertIn(b"hello", request.body)
                return json_response({"md5": "5d41402abc4b2a76b9719d911017c592"})
            if params.get("method") == "create":
                body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
                self.assertEqual(body["isdir"], "0")
                self.assertIn("5d41402abc4b2a76b9719d911017c592", body["block_list"])
                return json_response({"errno": 0, "path": "/apps/demo/a.txt"})
            raise AssertionError(params.get("method"))

        result = api.upload_file(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "a.txt",
            "/apps/demo/a.txt",
            b"hello",
            True,
        )
        self.assertTrue(result.payload["ok"], result.payload)
        self.assertEqual(result.payload["createCalled"], True)
        self.assertEqual([query_of(call.url)["method"] for call in calls], ["precreate", "locateupload", "upload", "create"])

    def test_multi_slice_uses_precreate_partseq_and_creates_once(self):
        content = b"abcdefghij"
        calls = []

        def handler(request):
            calls.append(request)
            params = query_of(request.url)
            if params.get("method") == "precreate":
                body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
                blocks = json.loads(body["block_list"])
                self.assertEqual(len(blocks), 3)
                self.assertEqual(blocks[0], api._md5(b"abcd"))
                self.assertEqual(blocks[2], api._md5(b"ij"))
                return json_response({"errno": 0, "uploadid": "up-2", "block_list": [2, 0]})
            if params.get("method") == "locateupload":
                return json_response({"error_code": 0, "servers": [{"server": "https://c.pcs.baidu.com"}]})
            if params.get("method") == "upload":
                partseq = int(params["partseq"])
                chunk = {0: b"abcd", 2: b"ij"}[partseq]
                self.assertIn(chunk, request.body)
                return json_response({"md5": api._md5(chunk)})
            if params.get("method") == "create":
                body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
                self.assertEqual(
                    json.loads(body["block_list"]),
                    [api._md5(b"abcd"), api._md5(b"efgh"), api._md5(b"ij")],
                )
                self.assertEqual(body["uploadid"], "up-2")
                self.assertEqual(body["size"], "10")
                return json_response({"errno": 0, "path": "/apps/demo/a.txt"})
            raise AssertionError(params.get("method"))

        result = api.upload_file(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "a.txt",
            "/apps/demo/a.txt",
            content,
            True,
            slice_size=4,
        )
        methods = [query_of(call.url)["method"] for call in calls]
        self.assertEqual(methods, ["precreate", "locateupload", "upload", "upload", "create"])
        self.assertEqual([query_of(call.url)["partseq"] for call in calls if query_of(call.url).get("method") == "upload"], ["2", "0"])
        self.assertEqual(methods.count("create"), 1)
        self.assertTrue(result.payload["ok"], result.payload)

    def test_slice_error_does_not_create(self):
        calls = []

        def handler(request):
            calls.append(request)
            params = query_of(request.url)
            if params.get("method") == "precreate":
                return json_response({"errno": 0, "uploadid": "up-err", "block_list": [0, 1]})
            if params.get("method") == "locateupload":
                return json_response({"error_code": 0, "servers": [{"server": "https://c.pcs.baidu.com"}]})
            if params.get("method") == "upload" and params.get("partseq") == "0":
                return json_response({"md5": api._md5(b"abcd")})
            if params.get("method") == "upload":
                return json_response({"errno": 31363, "errmsg": "missing slice"})
            raise AssertionError("create must not run")

        result = api.upload_file(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "a.txt",
            "/apps/demo/a.txt",
            b"abcdefgh",
            True,
            slice_size=4,
        )
        self.assertFalse(result.payload["ok"])
        self.assertFalse(result.payload["createCalled"])
        self.assertEqual(result.payload["uploadid"], "up-err")
        self.assertNotIn("create", [query_of(call.url)["method"] for call in calls])

    def test_resume_uploads_only_pending_slice_and_creates_once(self):
        calls = []

        def handler(request):
            calls.append(request)
            params = query_of(request.url)
            if params.get("method") == "precreate":
                body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
                self.assertEqual(body["uploadid"], "up-resume")
                return json_response({"errno": 0, "uploadid": "up-resume", "block_list": [1]})
            if params.get("method") == "locateupload":
                return json_response({"error_code": 0, "servers": [{"server": "https://c.pcs.baidu.com"}]})
            if params.get("method") == "upload":
                self.assertEqual(params["partseq"], "1")
                return json_response({"md5": api._md5(b"ef")})
            if params.get("method") == "create":
                body = query_of("https://example.invalid/?" + request.body.decode("utf-8"))
                self.assertEqual(json.loads(body["block_list"]), [api._md5(b"abcd"), api._md5(b"ef")])
                return json_response({"errno": 0, "path": "/apps/demo/a.txt"})
            raise AssertionError(params.get("method"))

        result = api.upload_file(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "a.txt",
            "/apps/demo/a.txt",
            b"abcdef",
            True,
            resume_uploadid="up-resume",
            slice_size=4,
        )
        methods = [query_of(call.url)["method"] for call in calls]
        self.assertEqual(methods, ["precreate", "locateupload", "upload", "create"])
        self.assertEqual(methods.count("create"), 1)
        self.assertTrue(result.payload["ok"], result.payload)

    def test_empty_pending_creates_once_without_slice_upload(self):
        calls = []

        def handler(request):
            calls.append(request)
            params = query_of(request.url)
            if params.get("method") == "precreate":
                return json_response({"errno": 0, "uploadid": "up-rapid", "block_list": []})
            if params.get("method") == "create":
                return json_response({"errno": 0, "path": "/apps/demo/a.txt"})
            raise AssertionError(params.get("method"))

        result = api.upload_file(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "a.txt",
            "/apps/demo/a.txt",
            b"hello",
            True,
        )
        self.assertEqual([query_of(call.url)["method"] for call in calls], ["precreate", "create"])
        self.assertTrue(result.payload["createCalled"])
        self.assertTrue(result.payload["ok"])

    def test_download_refuses_non_baidu_dlink_before_sending_token(self):
        def handler(request):
            return json_response({"errno": 0, "list": [{"dlink": "https://evil.example/file"}]})

        def stream_to(request, output):
            raise AssertionError("token must not be sent")

        result = api.download_fsid(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "123",
            stream_to,
            "out.bin",
            True,
        )
        self.assertFalse(result.payload["ok"])
        self.assertIn("token was not sent", result.payload["detail"])

    def test_download_appends_token_to_official_dlink(self):
        captured = {}

        def handler(request):
            return json_response({"errno": 0, "list": [{"dlink": "https://d.pcs.baidu.com/file/demo?fid=1"}]})

        def stream_to(request, output):
            captured["url"] = request.url
            captured["ua"] = request.headers["User-Agent"]
            return 4

        result = api.download_fsid(
            api.Config(access_token="token-value-ok"),
            FakeTransport(handler),
            "123",
            stream_to,
            "out.bin",
            True,
        )
        self.assertTrue(result.payload["ok"])
        self.assertIn("access_token=token-value-ok", captured["url"])
        self.assertEqual(captured["ua"], "pan.baidu.com")
        self.assertNotIn("token-value-ok", json.dumps({k: v for k, v in result.payload.items() if k != "detail"}))

    def test_cli_status_entrypoint(self):
        env = dict(os.environ)
        for name in (
            "BAIDU_NETDISK_ACCESS_TOKEN",
            "BAIDU_NETDISK_APP_KEY",
            "BAIDU_NETDISK_SECRET_KEY",
            "BAIDU_NETDISK_REFRESH_TOKEN",
        ):
            env.pop(name, None)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "netdisk.py"), "status"],
            check=False,
            capture_output=True,
            env=env,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(payload["state"], "unavailable")
        self.assertFalse(payload["upstreamCalled"])

    def test_plugin_manifest_pins_official_mcp(self):
        manifest = json.loads((ROOT / ".omnimind-plugin" / "plugin.json").read_text(encoding="utf-8"))
        server = manifest["mcpServers"]["baidu-netdisk"]
        self.assertEqual(server["type"], "sse")
        self.assertEqual(server["url"], api.OFFICIAL_MCP_SSE)
        self.assertEqual(server["headers"]["Authorization"], "Bearer ${user_config.access_token}")
        self.assertNotIn("default", manifest["userConfig"]["access_token"])
        self.assertTrue(manifest["userConfig"]["access_token"]["sensitive"])
        source = json.loads((ROOT / "SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual(source["stableId"], "proto:market:百度网盘")
        self.assertEqual(source["officialMcp"]["url"], server["url"])
        self.assertIsNone(source["icon"]["file"])


if __name__ == "__main__":
    unittest.main()
