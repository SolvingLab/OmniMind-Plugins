"""Offline checks for the meeting-minutes adapter. These are not a live transcription PASS."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import minutes


class FakeTransport(minutes.Transport):
    def __init__(self, routes: list[tuple[str, str, dict]]) -> None:
        self.routes = list(routes)
        self.calls: list[tuple[str, str, bytes | None]] = []

    def request(self, method, url, headers, body, timeout):  # noqa: ANN001
        self.calls.append((method, url, body))
        if not self.routes:
            raise AssertionError(f"unexpected {method} {url}")
        expect_method, expect_url, payload = self.routes.pop(0)
        if method != expect_method or url != expect_url:
            raise AssertionError(f"{method} {url} != {expect_method} {expect_url}")
        if "Authorization" in headers and headers["Authorization"] == "test-key":
            pass
        return minutes.Response(200, json.dumps(payload).encode("utf-8"), url)


class MinutesTests(unittest.TestCase):
    def test_missing_key_does_not_call_network(self) -> None:
        transport = FakeTransport([])
        with tempfile.TemporaryDirectory() as directory:
            out = str(Path(directory) / "minutes.json")
            code = minutes.main(
                ["write", "--audio-url", "https://example.com/meeting.mp3", "--out", out],
                env={},
                transport=transport,
            )
        self.assertEqual(code, 2)
        self.assertEqual(transport.calls, [])

    def test_request_bodies_are_one_task_each(self) -> None:
        summary = minutes.summarization_body("https://cdn.example/upload/1")
        actions = minutes.action_items_body("https://cdn.example/upload/1")
        self.assertEqual(minutes.request_task_names(summary), ["summarization"])
        self.assertEqual(minutes.request_task_names(actions), ["action_items"])
        self.assertEqual(summary["speech_understanding"]["request"]["summarization"]["summary_type"], "paragraph")
        self.assertTrue(actions["speech_understanding"]["request"]["action_items"]["include_decisions"])

    def test_write_parses_official_fields_and_trace_is_local(self) -> None:
        transcript_id = "tr_summary"
        action_id = "tr_actions"
        summary_transcript = {
            "id": transcript_id,
            "status": "completed",
            "words": [
                {"text": "alpha", "start": 200, "end": 400},
                {"text": "later", "start": 40000, "end": 40100},
            ],
            "speech_understanding": {
                "response": {
                    "summarization": {
                        "status": "success",
                        "summary": [
                            {
                                "start": 240,
                                "end": 37100,
                                "text": "Chapter summary from the official field.",
                                "headline": "Chapter",
                            }
                        ],
                    }
                }
            },
        }
        action_transcript = {
            "id": action_id,
            "status": "completed",
            "words": [{"text": "decide", "start": 9000, "end": 9800}],
            "speech_understanding": {
                "response": {
                    "action_items": {
                        "status": "success",
                        "items": [
                            {
                                "action_item": "Record the decision.",
                                "quote": "We decided.",
                                "timestamp": 9520,
                            }
                        ],
                    }
                }
            },
        }
        transport = FakeTransport(
            [
                ("POST", "https://api.assemblyai.com/v2/transcript", {"id": transcript_id, "status": "queued"}),
                ("GET", f"https://api.assemblyai.com/v2/transcript/{transcript_id}", summary_transcript),
                ("POST", "https://api.assemblyai.com/v2/transcript", {"id": action_id, "status": "queued"}),
                ("GET", f"https://api.assemblyai.com/v2/transcript/{action_id}", action_transcript),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "minutes.json"
            code = minutes.main(
                [
                    "write",
                    "--audio-url",
                    "https://example.com/meeting.mp3",
                    "--out",
                    str(out),
                    "--wait-seconds",
                    "5",
                    "--interval-seconds",
                    "0",
                ],
                env={"ASSEMBLYAI_API_KEY": "test-key"},
                transport=transport,
            )
            self.assertEqual(code, 0)
            document = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "completed")
            self.assertFalse(document["nativePass"])
            self.assertEqual(document["minutes"][0]["start"], 240)
            self.assertEqual(document["minutes"][0]["end"], 37100)
            self.assertEqual(document["minutes"][0]["audioWords"], [{"text": "alpha", "start": 200, "end": 400}])
            self.assertEqual(document["actions"][0]["timestamp"], 9520)
            self.assertEqual(document["actions"][0]["quote"], "We decided.")
            posted = [json.loads(body) for method, url, body in transport.calls if method == "POST"]
            self.assertEqual(len(posted), 2)
            self.assertEqual(minutes.request_task_names(posted[0]), ["summarization"])
            self.assertEqual(minutes.request_task_names(posted[1]), ["action_items"])
            traced = minutes.trace_item(document, "m1")
            self.assertEqual(traced["audioSpan"]["start"], 240)
            self.assertEqual(traced["audioSpan"]["end"], 37100)
            self.assertEqual(traced["network"], "not_sent")
            action = minutes.trace_item(document, "a1")
            self.assertEqual(action["audioSpan"]["timestamp"], 9520)
            self.assertEqual(action["quote"], "We decided.")
            self.assertNotIn("end", action["audioSpan"])

    def test_missing_span_is_not_invented(self) -> None:
        items = minutes.parse_summary_items(
            {
                "speech_understanding": {
                    "response": {
                        "summarization": {
                            "summary": [{"text": "No time was returned."}],
                            "status": "success",
                        }
                    }
                }
            }
        )
        self.assertFalse(items[0]["traceable"])
        self.assertIsNone(items[0]["start"])
        self.assertIsNone(items[0]["end"])
        with self.assertRaises(minutes.AdapterError) as caught:
            minutes.trace_item({"minutes": items, "actions": []}, "m1")
        self.assertEqual(caught.exception.exit_code, 4)

    def test_other_base_url_is_refused_before_network(self) -> None:
        transport = FakeTransport([])
        with tempfile.TemporaryDirectory() as directory:
            code = minutes.main(
                ["write", "--audio-url", "https://example.com/a.mp3", "--out", str(Path(directory) / "out.json")],
                env={"ASSEMBLYAI_API_KEY": "test-key", "ASSEMBLYAI_BASE_URL": "https://evil.example"},
                transport=transport,
            )
        self.assertEqual(code, 2)
        self.assertEqual(transport.calls, [])

    def test_pending_does_not_claim_completion(self) -> None:
        transport = FakeTransport(
            [
                ("POST", "https://api.assemblyai.com/v2/transcript", {"id": "tr_wait", "status": "queued"}),
                ("GET", "https://api.assemblyai.com/v2/transcript/tr_wait", {"id": "tr_wait", "status": "processing"}),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "minutes.json"
            code = minutes.main(
                [
                    "write",
                    "--audio-url",
                    "https://example.com/meeting.mp3",
                    "--out",
                    str(out),
                    "--wait-seconds",
                    "0",
                    "--interval-seconds",
                    "0",
                ],
                env={"ASSEMBLYAI_API_KEY": "test-key"},
                transport=transport,
            )
            document = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(code, 3)
        self.assertEqual(document["status"], "pending")
        self.assertEqual(document["minutes"], [])
        self.assertEqual(document["minutesJob"]["transcriptId"], "tr_wait")


if __name__ == "__main__":
    unittest.main()
