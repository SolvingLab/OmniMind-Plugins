import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
import tiktok_business  # noqa: E402

ICON_SHA256 = "6f54ac8d325faacea8935bdc44cbed60206a6b408641799e5fea1cba7c1a0af7"
REPO = Path(__file__).resolve().parents[4]


def clean_env():
    env = {}
    for key in ("PATH", "SYSTEMROOT", "PATHEXT", "COMSPEC", "TEMP", "TMP"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


class AdapterTests(unittest.TestCase):
    def test_status_missing_token_does_not_claim_a_live_call(self):
        payload = tiktok_business.status_payload(env={})
        self.assertEqual(payload["unavailable"], "credentials_missing")
        self.assertFalse(payload["liveCall"])
        self.assertFalse(payload["accountConnected"])
        self.assertEqual(payload["stableId"], "proto:market:TikTok for Business")
        encoded = json.dumps(payload)
        self.assertNotIn("secret-value", encoded)

    def test_cli_status_exit_2_without_token(self):
        completed = subprocess.run(
            [sys.executable, str(PACKAGE / "scripts" / "tiktok_business.py"), "status"],
            check=False,
            capture_output=True,
            env=clean_env(),
        )
        stdout = completed.stdout.decode("utf-8")
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(stdout)
        self.assertEqual(payload["unavailable"], "credentials_missing")
        self.assertNotIn("TIKTOK_BUSINESS_ACCESS_TOKEN", stdout)

    def test_campaign_create_refuses_missing_token_without_network(self):
        called = []

        def opener(request, timeout=30):
            called.append(request)
            raise AssertionError("network must not be called")

        result = tiktok_business.call_operation(
            "campaign_create",
            body={"advertiser_id": "1", "campaign_name": "n", "objective_type": "TRAFFIC"},
            env={},
            opener=opener,
        )
        self.assertEqual(result["unavailable"], "credentials_missing")
        self.assertEqual(called, [])

    def test_campaign_create_request_uses_official_path_and_header(self):
        prepared = tiktok_business.build_call(
            "campaign_create",
            body={"advertiser_id": "7100", "campaign_name": "spring", "objective_type": "TRAFFIC"},
            env={"TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value"},
        )
        request = prepared["request"]
        parsed = urllib.parse.urlsplit(request["url"])
        self.assertEqual(request["method"], "POST")
        self.assertEqual(parsed.hostname, "business-api.tiktok.com")
        self.assertEqual(parsed.path, "/open_api/v1.3/campaign/create/")
        self.assertEqual(parsed.query, "")
        self.assertEqual(request["headers"]["Access-Token"], "token-value")
        self.assertNotIn("token-value", request["url"])
        body = json.loads(request["data"].decode("utf-8"))
        self.assertEqual(body["objective_type"], "TRAFFIC")
        view = tiktok_business.prepare_view(prepared)
        self.assertNotIn("token-value", json.dumps(view))
        self.assertTrue(view["hasAccessTokenHeader"])

    def test_campaign_create_requires_pinned_body_fields(self):
        result = tiktok_business.build_call(
            "campaign_create",
            body={"campaign_name": "spring"},
            env={"TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value"},
        )
        self.assertEqual(result["unavailable"], "required_fields_missing")
        self.assertIn("advertiser_id", result["missing"])
        self.assertIn("objective_type", result["missing"])

    def test_report_query_json_encodes_lists(self):
        prepared = tiktok_business.build_call(
            "report_integrated_get",
            query={
                "report_type": "BASIC",
                "dimensions": ["campaign_id", "stat_time_day"],
                "metrics": ["spend", "impressions"],
            },
            env={"TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value"},
        )
        parsed = urllib.parse.urlsplit(prepared["request"]["url"])
        self.assertEqual(parsed.path, "/open_api/v1.3/report/integrated/get/")
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertEqual(query["report_type"], "BASIC")
        self.assertEqual(json.loads(query["dimensions"]), ["campaign_id", "stat_time_day"])
        self.assertEqual(json.loads(query["metrics"]), ["spend", "impressions"])

    def test_oauth_token_exchange_has_no_access_token_header(self):
        prepared = tiktok_business.build_call(
            "oauth2_access_token",
            body={"app_id": "app", "auth_code": "code-value", "secret": "secret-value"},
            env={},
        )
        self.assertNotIn("Access-Token", prepared["request"]["headers"])
        self.assertNotIn("secret-value", prepared["request"]["url"])
        view = tiktok_business.prepare_view(prepared)
        self.assertNotIn("secret-value", json.dumps(view))
        self.assertNotIn("code-value", json.dumps(view))

    def test_advertiser_get_puts_secret_in_query_and_redacts_transport_errors(self):
        def opener(request, timeout=30):
            raise urllib.error.URLError("boom " + request.full_url)

        result = tiktok_business.call_operation(
            "oauth2_advertiser_get",
            query={"app_id": "app", "secret": "secret-value"},
            env={"TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value"},
            opener=opener,
        )
        self.assertTrue(result["transportError"])
        self.assertNotIn("secret-value", result["error"])
        self.assertNotIn("token-value", result["error"])
        self.assertIn("[redacted]", result["error"])

    def test_api_code_is_not_rewritten_as_success(self):
        class Response:
            status = 200

            def read(self):
                return json.dumps({"code": 40001, "message": "invalid", "request_id": "r"}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        result = tiktok_business.call_operation(
            "campaign_get",
            query={"advertiser_id": "7100"},
            env={"TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value"},
            opener=lambda request, timeout=30: Response(),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["apiCode"], 40001)
        self.assertTrue(result["liveCall"])

    def test_unofficial_base_is_rejected(self):
        result = tiktok_business.build_call(
            "campaign_get",
            query={"advertiser_id": "7100"},
            env={
                "TIKTOK_BUSINESS_ACCESS_TOKEN": "token-value",
                "TIKTOK_BUSINESS_API_BASE": "https://example.invalid",
            },
        )
        self.assertEqual(result["unavailable"], "unofficial_base_rejected")

    def test_mcp_status_and_tool_list(self):
        stdin = io.StringIO(
            "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                    json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "tiktok_business_status", "arguments": {}}}),
                ]
            )
            + "\n"
        )
        messages = []
        previous = os.environ.get("TIKTOK_BUSINESS_ACCESS_TOKEN")
        os.environ.pop("TIKTOK_BUSINESS_ACCESS_TOKEN", None)
        try:
            tiktok_business.serve_mcp(stdin=stdin, stdout_write=messages.append)
        finally:
            if previous is None:
                os.environ.pop("TIKTOK_BUSINESS_ACCESS_TOKEN", None)
            else:
                os.environ["TIKTOK_BUSINESS_ACCESS_TOKEN"] = previous
        self.assertEqual(messages[0]["id"], 1)
        self.assertEqual(messages[0]["result"]["protocolVersion"], "2024-11-05")
        names = [tool["name"] for tool in messages[1]["result"]["tools"]]
        self.assertEqual(names, ["tiktok_business_status", "tiktok_business_call"])
        status = json.loads(messages[2]["result"]["content"][0]["text"])
        self.assertTrue(messages[2]["result"]["isError"])
        self.assertEqual(status["unavailable"], "credentials_missing")

    def test_icon_bytes_match_pinned_simple_icons_file(self):
        package_icon = (PACKAGE / "assets" / "icon.svg").read_bytes()
        brand_icon = (REPO / "packages" / "ui" / "src" / "assets" / "plugin-brands" / "tiktok-for-business.svg").read_bytes()
        self.assertEqual(hashlib.sha256(package_icon).hexdigest(), ICON_SHA256)
        self.assertEqual(package_icon, brand_icon)
        self.assertEqual(len(package_icon), 707)


if __name__ == "__main__":
    unittest.main()
