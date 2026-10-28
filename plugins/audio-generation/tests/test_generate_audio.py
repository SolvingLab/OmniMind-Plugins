"""Focused checks for the audio-generation adapter. Not a native acceptance pass."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_audio  # noqa: E402
import mcp_server  # noqa: E402


class GenerateAudioTests(unittest.TestCase):
    def test_official_endpoint_is_pinned(self) -> None:
        self.assertEqual(
            generate_audio.OFFICIAL_ENDPOINT,
            "https://api.elevenlabs.io/v1/sound-generation",
        )
        self.assertEqual(generate_audio.MODEL_ID, "eleven_text_to_sound_v2")

    def test_missing_key_does_not_call_transport(self) -> None:
        called = {"n": 0}

        def transport(payload: dict, api_key: str) -> tuple[int, str, bytes]:
            called["n"] += 1
            raise AssertionError("transport should not run")

        result = generate_audio.generate(
            "rain on a tin roof",
            "unused.mp3",
            api_key="",
            transport=transport,
        )
        self.assertEqual(result["status"], "setup_required")
        self.assertFalse(result["ok"])
        self.assertEqual(called["n"], 0)
        self.assertNotIn("outputPath", result)

    def test_request_matches_official_schema_and_writes_audio(self) -> None:
        seen: dict = {}

        def transport(payload: dict, api_key: str) -> tuple[int, str, bytes]:
            seen["payload"] = payload
            seen["api_key"] = api_key
            return 200, "audio/mpeg", b"ID3fake-audio"

        destination = Path(self.id().replace(".", "_") + ".mp3")
        try:
            result = generate_audio.generate(
                "  rain on a tin roof  ",
                str(destination),
                api_key="test-key-not-a-secret",
                duration_seconds=2.5,
                prompt_influence=0.4,
                loop=True,
                transport=transport,
            )
            self.assertEqual(seen["payload"]["text"], "rain on a tin roof")
            self.assertEqual(seen["payload"]["model_id"], "eleven_text_to_sound_v2")
            self.assertEqual(seen["payload"]["duration_seconds"], 2.5)
            self.assertEqual(seen["payload"]["prompt_influence"], 0.4)
            self.assertIs(seen["payload"]["loop"], True)
            self.assertEqual(seen["api_key"], "test-key-not-a-secret")
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["ok"])
            self.assertEqual(result["mimeType"], "audio/mpeg")
            self.assertEqual(destination.read_bytes(), b"ID3fake-audio")
            self.assertNotIn("test-key-not-a-secret", json.dumps(result))
        finally:
            destination.unlink(missing_ok=True)

    def test_json_body_is_not_success(self) -> None:
        def transport(payload: dict, api_key: str) -> tuple[int, str, bytes]:
            return 200, "application/json", b'{"detail":"nope"}'

        result = generate_audio.generate(
            "a door closing",
            "nope.mp3",
            api_key="k",
            transport=transport,
        )
        self.assertEqual(result["status"], "invalid-response")
        self.assertFalse(result["ok"])
        self.assertFalse(Path("nope.mp3").exists())

    def test_auth_failure_is_not_success(self) -> None:
        def transport(payload: dict, api_key: str) -> tuple[int, str, bytes]:
            return 401, "application/json", b'{"detail":"unauthorized"}'

        result = generate_audio.generate(
            "a door closing",
            "denied.mp3",
            api_key="k",
            transport=transport,
        )
        self.assertEqual(result["status"], "not-authenticated")
        self.assertFalse(result["ok"])
        self.assertFalse(Path("denied.mp3").exists())

    def test_duration_guard_matches_official_bounds(self) -> None:
        result = generate_audio.generate(
            "a short click",
            "x.mp3",
            api_key="k",
            duration_seconds=0.1,
            transport=lambda payload, api_key: (_ for _ in ()).throw(AssertionError("network")),
        )
        self.assertEqual(result["status"], "invalid-prompt")
        self.assertFalse(result["ok"])

    def test_stdout_redacts_key(self) -> None:
        secret = "super-secret-value"
        previous = os.environ.get(generate_audio.ENV_KEY)
        os.environ[generate_audio.ENV_KEY] = secret
        try:
            payload = generate_audio._result(
                "upstream-error",
                ok=False,
                message=f"upstream said {secret}",
            )
            encoded = generate_audio.redact(json.dumps(payload), secret)
        finally:
            if previous is None:
                os.environ.pop(generate_audio.ENV_KEY, None)
            else:
                os.environ[generate_audio.ENV_KEY] = previous
        self.assertNotIn(secret, encoded)
        self.assertIn("[redacted]", encoded)

    def test_cli_missing_key_exits_before_network(self) -> None:
        env = os.environ.copy()
        env.pop(generate_audio.ENV_KEY, None)
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_audio.py"),
                "--text",
                "soft room tone",
                "--output",
                "should-not-exist.mp3",
            ],
            cwd=SCRIPTS,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "setup_required")
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["configured"])
        self.assertIn("No request was sent.", payload["message"])
        self.assertFalse((SCRIPTS / "should-not-exist.mp3").exists())


class McpServerTests(unittest.TestCase):
    def test_missing_key_tool_call_is_error(self) -> None:
        env = os.environ.copy()
        env.pop(generate_audio.ENV_KEY, None)
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS / "mcp_server.py")],
            cwd=SCRIPTS,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout
        try:
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
            )
            init = self._recv(proc)
            self.assertEqual(init["result"]["serverInfo"]["name"], "audio-generation")
            self._send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            self._send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            listed = self._recv(proc)
            self.assertEqual(listed["result"]["tools"][0]["name"], "generate_audio")
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_audio",
                        "arguments": {
                            "text": "distant thunder",
                            "output_path": "thunder.mp3",
                        },
                    },
                },
            )
            called = self._recv(proc)
            self.assertTrue(called["result"]["isError"])
            body = json.loads(called["result"]["content"][0]["text"])
            self.assertEqual(body["status"], "setup_required")
            self.assertFalse(body["ok"])
        finally:
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
            proc.kill()
            proc.wait(timeout=5)

    def _send(self, proc: subprocess.Popen, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        assert proc.stdin
        proc.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data)
        proc.stdin.flush()

    def _recv(self, proc: subprocess.Popen) -> dict:
        assert proc.stdout
        headers: dict[str, str] = {}
        while True:
            line = proc.stdout.readline()
            if line in (b"\r\n", b"\n"):
                break
            decoded = line.decode("ascii")
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        length = int(headers["content-length"])
        return json.loads(proc.stdout.read(length).decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
