import hashlib
import io
import json
import os
import sys
import unittest
import urllib.parse
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))

import tencent_ads  # noqa: E402


class Response:
    def __init__(self, status, payload):
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def close(self):
        return None

    def getcode(self):
        return self.status


class RecordingOpener:
    def __init__(self, status=200, payload=None):
        self.calls = []
        self.status = status
        self.payload = {"code": 0, "data": {"list": []}} if payload is None else payload

    def __call__(self, request, timeout=None):
        self.calls.append((request, timeout))
        return Response(self.status, self.payload)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        for name in (
            "TENCENT_ADS_ACCESS_TOKEN",
            "TENCENT_ADS_ACCOUNT_ID",
            "TENCENT_ADS_API_BASE",
            "TENCENT_ADS_USER_TOKEN",
            "TENCENT_ADS_CLIENT_ID",
            "TENCENT_ADS_CLIENT_SECRET",
        ):
            os.environ.pop(name, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def capture(self, argv, opener=None):
        buffer = io.StringIO()
        previous = sys.stdout
        sys.stdout = buffer
        try:
            code = tencent_ads.main(argv, opener=opener)
        finally:
            sys.stdout = previous
        return code, json.loads(buffer.getvalue())

    def test_status_missing_credentials_does_not_call_network(self):
        opener = RecordingOpener()
        code, payload = self.capture(["status"], opener)
        self.assertEqual(code, 2)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["state"], "setup_required")
        self.assertIn("TENCENT_ADS_ACCESS_TOKEN", payload["missing"])
        self.assertEqual(opener.calls, [])
        self.assertFalse(payload["liveDelivery"])

    def test_goals_are_pinned_and_not_a_live_call(self):
        opener = RecordingOpener()
        code, payload = self.capture(["goals"], opener)
        self.assertEqual(code, 0)
        self.assertEqual(payload["count"], 100)
        self.assertIn("SMART_DELIVERY_GOAL_LEADS", payload["values"])
        self.assertFalse(payload["liveApi"])
        self.assertEqual(opener.calls, [])

    def test_adgroups_get_uses_official_v3_path_and_auth_query(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        opener = RecordingOpener()
        code, payload = self.capture(["adgroups-get"], opener)
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 30)
        parts = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(parts.scheme + "://" + parts.netloc + parts.path, "https://api.e.qq.com/v3.0/adgroups/get")
        query = urllib.parse.parse_qs(parts.query)
        self.assertEqual(query["access_token"], ["token-value"])
        self.assertEqual(query["account_id"], ["12345"])
        self.assertEqual(len(query["nonce"][0]), 16)
        self.assertTrue(query["timestamp"][0].isdigit())
        fields = json.loads(query["fields"][0])
        self.assertIn("smart_bid_type", fields)
        self.assertIn("smart_cost_cap", fields)
        self.assertIn("smart_targeting_status", fields)
        self.assertNotIn("token-value", payload["requestUrl"])

    def test_disallowed_base_is_rejected(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        os.environ["TENCENT_ADS_API_BASE"] = "https://business-api.tiktok.com"
        opener = RecordingOpener()
        code, payload = self.capture(["adgroups-get"], opener)
        self.assertEqual(code, 2)
        self.assertEqual(opener.calls, [])
        self.assertIn("TENCENT_ADS_API_BASE", payload["message"])

    def test_add_without_execute_does_not_post(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        body = PACKAGE / "tests" / "fixture-add.json"
        body.write_text(
            json.dumps({"adgroup_name": "not-sent", "smart_bid_type": "SMART_BID_TYPE_SYSTEMATIC"}),
            encoding="utf-8",
        )
        opener = RecordingOpener()
        try:
            code, payload = self.capture(["adgroups-add", "--body", str(body)], opener)
        finally:
            body.unlink(missing_ok=True)
        self.assertEqual(code, 2)
        self.assertEqual(payload["state"], "execution_required")
        self.assertFalse(payload["networkCalled"])
        self.assertEqual(opener.calls, [])
        self.assertEqual(payload["body"]["account_id"], 12345)
        self.assertEqual(payload["body"]["smart_bid_type"], "SMART_BID_TYPE_SYSTEMATIC")

    def test_add_execute_posts_official_path(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        body = PACKAGE / "tests" / "fixture-add.json"
        body.write_text(
            json.dumps(
                {
                    "adgroup_name": "smart",
                    "smart_bid_type": "SMART_BID_TYPE_SYSTEMATIC",
                    "smart_targeting_mode": "SMART_TARGETING_MANUAL",
                    "is_smart_delivery_upgrade_project": True,
                }
            ),
            encoding="utf-8",
        )
        opener = RecordingOpener(payload={"code": 0, "data": {"adgroup_id": 9}})
        try:
            code, payload = self.capture(["adgroups-add", "--body", str(body), "--execute"], opener)
        finally:
            body.unlink(missing_ok=True)
        self.assertEqual(code, 0)
        request, _timeout = opener.calls[0]
        self.assertEqual(request.get_method(), "POST")
        parts = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(parts.path, "/v3.0/adgroups/add")
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["account_id"], 12345)
        self.assertTrue(sent["is_smart_delivery_upgrade_project"])
        self.assertEqual(payload["body"]["data"]["adgroup_id"], 9)

    def test_invalid_goal_is_rejected_before_network(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        body = PACKAGE / "tests" / "fixture-add.json"
        body.write_text(
            json.dumps({"smart_delivery_scene_spec": {"smart_delivery_goal": "NOT_A_PINNED_GOAL"}}),
            encoding="utf-8",
        )
        opener = RecordingOpener()
        try:
            code, payload = self.capture(["adgroups-update", "--body", str(body), "--execute"], opener)
        finally:
            body.unlink(missing_ok=True)
        self.assertEqual(code, 1)
        self.assertIn("smart_delivery_goal", payload["message"])
        self.assertEqual(opener.calls, [])

    def test_api_code_nonzero_is_not_success(self):
        os.environ["TENCENT_ADS_ACCESS_TOKEN"] = "token-value"
        os.environ["TENCENT_ADS_ACCOUNT_ID"] = "12345"
        opener = RecordingOpener(payload={"code": 11000, "message": "denied"})
        code, payload = self.capture(["adgroups-get"], opener)
        self.assertEqual(code, 3)
        self.assertEqual(payload["body"]["code"], 11000)

    def test_icon_and_license_hashes(self):
        icon = (PACKAGE / "assets" / "icon.png").read_bytes()
        license_bytes = (PACKAGE / "LICENSE").read_bytes()
        self.assertEqual(hashlib.sha256(icon).hexdigest(), "c309e6bd25510425f0f9798df993f13e41a6170604670744076e5b76d9cab025")
        self.assertEqual(hashlib.sha256(license_bytes).hexdigest(), "8b36af1f8c4f150bf0cbfc84fd008d6459ccd9f7d26959dc889e676c76c0a92c")
        self.assertTrue(icon.startswith(b"\x89PNG"))
        brand = PACKAGE.parents[2] / "packages" / "ui" / "src" / "assets" / "plugin-brands" / "tencent-ads.png"
        if brand.is_file():
            self.assertEqual(hashlib.sha256(brand.read_bytes()).hexdigest(), hashlib.sha256(icon).hexdigest())

    def test_nonce_matches_sdk_slice(self):
        self.assertEqual(tencent_ads.nonce_from_uuid("123e4567-e89b-12d3-a456-426614174000"), "123e4567e89b12d3")


if __name__ == "__main__":
    unittest.main()
