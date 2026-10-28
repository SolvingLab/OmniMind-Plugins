"""Generate audio from a text description.

Official contract, fetched 2026-10-15:
POST https://api.elevenlabs.io/v1/sound-generation
Header xi-api-key: $ELEVENLABS_API_KEY
Docs: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert

The text is a description of the sound to generate. This does not read the
text aloud and does not call any other product. A missing key exits before
any network call.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

OFFICIAL_ENDPOINT = "https://api.elevenlabs.io/v1/sound-generation"
OFFICIAL_DOCS = "https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert"
MODEL_ID = "eleven_text_to_sound_v2"
ENV_KEY = "ELEVENLABS_API_KEY"
STABLE_ID = "proto:market:音频生成"
MAX_AUDIO_BYTES = 25 * 1024 * 1024
USER_AGENT = "omnimind-audio-generation/0.1.0"

Transport = Callable[[dict, str], tuple[int, str, bytes]]


class LocalRejection(Exception):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def api_key_from_env(environ: dict[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    return source.get(ENV_KEY, "").strip()


def build_payload(
    text: str,
    *,
    duration_seconds: float | None = None,
    loop: bool | None = None,
    prompt_influence: float | None = None,
) -> dict:
    prompt = text.strip()
    if not prompt:
        raise LocalRejection("invalid-prompt", "text description is empty")
    payload: dict = {"text": prompt, "model_id": MODEL_ID}
    if duration_seconds is not None:
        if duration_seconds < 0.5 or duration_seconds > 30:
            raise LocalRejection(
                "invalid-prompt",
                "duration_seconds must be between 0.5 and 30",
            )
        payload["duration_seconds"] = duration_seconds
    if prompt_influence is not None:
        if prompt_influence < 0 or prompt_influence > 1:
            raise LocalRejection(
                "invalid-prompt",
                "prompt_influence must be between 0 and 1",
            )
        payload["prompt_influence"] = prompt_influence
    if loop is not None:
        payload["loop"] = bool(loop)
    return payload


def official_transport(payload: dict, api_key: str) -> tuple[int, str, bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        OFFICIAL_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg, application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(MAX_AUDIO_BYTES + 1)
            return response.status, content_type, data
    except urllib.error.HTTPError as exc:
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        data = exc.read(MAX_AUDIO_BYTES + 1)
        return exc.code, content_type, data


def _looks_like_audio(content_type: str, body: bytes) -> bool:
    media = content_type.split(";", 1)[0].strip().lower()
    if media.startswith("audio/") and body and not _looks_like_json(body):
        return True
    if len(body) >= 3 and body[:3] == b"ID3":
        return True
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WAVE":
        return True
    if len(body) >= 4 and body[:4] == b"OggS":
        return True
    if len(body) >= 2 and body[0] == 0xFF and (body[1] & 0xE0) == 0xE0:
        return True
    return False


def _looks_like_json(body: bytes) -> bool:
    stripped = body.lstrip()
    return stripped.startswith(b"{") or stripped.startswith(b"[")


def interpret_response(status: int, content_type: str, body: bytes) -> dict:
    if len(body) > MAX_AUDIO_BYTES:
        return {
            "status": "invalid-response",
            "ok": False,
            "httpStatus": status,
            "message": "upstream body exceeded the package byte guard",
        }
    if status == 401 or status == 403:
        return {
            "status": "not-authenticated",
            "ok": False,
            "httpStatus": status,
            "message": "official sound-generation endpoint rejected the API key",
        }
    if status == 422:
        return {
            "status": "invalid-prompt",
            "ok": False,
            "httpStatus": status,
            "message": "official sound-generation endpoint rejected the description",
        }
    if status != 200:
        return {
            "status": "upstream-error",
            "ok": False,
            "httpStatus": status,
            "message": "official sound-generation endpoint did not return audio",
        }
    if not _looks_like_audio(content_type, body):
        return {
            "status": "invalid-response",
            "ok": False,
            "httpStatus": status,
            "message": "upstream 200 was not an audio payload",
        }
    media = content_type.split(";", 1)[0].strip().lower() or "audio/mpeg"
    if not media.startswith("audio/"):
        media = "audio/mpeg"
    return {
        "status": "success",
        "ok": True,
        "httpStatus": status,
        "mimeType": media,
        "audio": body,
        "bytes": len(body),
    }


def _result(status: str, *, ok: bool, message: str, **extra: object) -> dict:
    payload = {
        "status": status,
        "ok": ok,
        "stableId": STABLE_ID,
        "function": "根据文字描述生成音频",
        "endpoint": OFFICIAL_ENDPOINT,
        "docs": OFFICIAL_DOCS,
        "modelId": MODEL_ID,
        "message": message,
    }
    payload.update(extra)
    return payload


def redact(text: str, secret: str) -> str:
    if secret and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def generate(
    text: str,
    output_path: str,
    *,
    api_key: str | None = None,
    duration_seconds: float | None = None,
    loop: bool | None = None,
    prompt_influence: float | None = None,
    transport: Transport | None = None,
) -> dict:
    key = (api_key if api_key is not None else api_key_from_env()).strip()
    if not key:
        return _result(
            "setup_required",
            ok=False,
            message=f"{ENV_KEY} is unset. No request was sent.",
            configured=False,
        )
    try:
        payload = build_payload(
            text,
            duration_seconds=duration_seconds,
            loop=loop,
            prompt_influence=prompt_influence,
        )
    except LocalRejection as exc:
        return _result(exc.status, ok=False, message=exc.message, configured=True)
    destination = Path(output_path)
    if not output_path.strip() or destination.exists() and destination.is_dir():
        return _result(
            "invalid-output",
            ok=False,
            message="output path must be a file path",
            configured=True,
        )
    if destination.parent and not destination.parent.exists():
        return _result(
            "invalid-output",
            ok=False,
            message="output directory does not exist",
            configured=True,
        )
    sender = transport or official_transport
    try:
        status, content_type, body = sender(payload, key)
    except (urllib.error.URLError, TimeoutError, OSError):
        return _result(
            "upstream-error",
            ok=False,
            message="official sound-generation endpoint was not reachable",
            configured=True,
        )
    interpreted = interpret_response(status, content_type, body)
    audio = interpreted.pop("audio", None)
    if interpreted["status"] != "success" or not isinstance(audio, bytes):
        interpreted_message = redact(str(interpreted.get("message", "")), key)
        return _result(
            str(interpreted["status"]),
            ok=False,
            message=interpreted_message,
            configured=True,
            httpStatus=interpreted.get("httpStatus"),
        )
    temporary = destination.with_suffix(destination.suffix + ".partial")
    temporary.write_bytes(audio)
    temporary.replace(destination)
    return _result(
        "success",
        ok=True,
        message="wrote audio generated from the text description",
        configured=True,
        httpStatus=interpreted.get("httpStatus"),
        mimeType=interpreted.get("mimeType"),
        bytes=interpreted.get("bytes"),
        outputPath=str(destination),
    )


def check_config() -> dict:
    configured = bool(api_key_from_env())
    if not configured:
        return _result(
            "setup_required",
            ok=False,
            message=f"{ENV_KEY} is unset. No request was sent.",
            configured=False,
        )
    return _result(
        "configured",
        ok=False,
        message="key is set; this check does not generate audio",
        configured=True,
    )


def emit(payload: dict) -> int:
    secret = api_key_from_env()
    encoded = redact(json.dumps(payload, ensure_ascii=False), secret)
    sys.stdout.write(encoded + "\n")
    if payload.get("status") == "success":
        return 0
    if payload.get("status") in {"setup_required", "invalid-prompt", "invalid-output", "configured"}:
        return 2
    return 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="根据文字描述生成音频")
    parser.add_argument("--text", help="text description of the sound to generate")
    parser.add_argument("--output", help="file path for the audio bytes")
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--prompt-influence", type=float)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="report whether ELEVENLABS_API_KEY is set; does not generate audio",
    )
    args = parser.parse_args(argv)
    if args.check_config:
        return emit(check_config())
    if not args.text or not args.output:
        return emit(
            _result(
                "invalid-prompt",
                ok=False,
                message="--text and --output are required",
                configured=bool(api_key_from_env()),
            )
        )
    return emit(
        generate(
            args.text,
            args.output,
            duration_seconds=args.duration_seconds,
            loop=True if args.loop else None,
            prompt_influence=args.prompt_influence,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
