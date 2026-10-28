"""Stdio MCP adapter for 根据文字描述生成音频.

Frames messages with Content-Length, the MCP stdio encoding. stdout is reserved
for protocol frames. A missing ELEVENLABS_API_KEY returns setup_required and
does not call the network.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import generate_audio

PROTOCOL = "2024-11-05"
SERVER = {"name": "audio-generation", "version": "0.1.0"}
TOOL = {
    "name": "generate_audio",
    "description": (
        "根据文字描述生成音频。text 是声音描述，不是朗读稿。"
        "未配置 ELEVENLABS_API_KEY 时返回 setup_required，不发送请求。"
    ),
    "inputSchema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "output_path"],
        "properties": {
            "text": {"type": "string", "description": "要生成的声音的文字描述"},
            "output_path": {"type": "string", "description": "输出音频文件路径"},
            "duration_seconds": {"type": "number", "minimum": 0.5, "maximum": 30},
            "loop": {"type": "boolean"},
            "prompt_influence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
}


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("ascii", errors="replace")
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def tool_result(result: dict[str, Any]) -> dict[str, Any]:
    secret = generate_audio.api_key_from_env()
    text = generate_audio.redact(json.dumps(result, ensure_ascii=False), secret)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": result.get("status") != "success",
    }


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method in {"notifications/initialized", "initialized"} and request_id is None:
        return None
    if method == "initialize":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        requested = params.get("protocolVersion")
        version = requested if isinstance(requested, str) and requested else PROTOCOL
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": [TOOL]}}
    if method == "tools/call":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        name = params.get("name")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if name != TOOL["name"]:
            result = generate_audio._result(
                "invalid-prompt",
                ok=False,
                message="unknown tool",
                configured=bool(generate_audio.api_key_from_env()),
            )
        else:
            text = arguments.get("text")
            output_path = arguments.get("output_path")
            if not isinstance(text, str) or not isinstance(output_path, str):
                result = generate_audio._result(
                    "invalid-prompt",
                    ok=False,
                    message="text and output_path must be strings",
                    configured=bool(generate_audio.api_key_from_env()),
                )
            else:
                duration = arguments.get("duration_seconds")
                influence = arguments.get("prompt_influence")
                loop = arguments.get("loop")
                result = generate_audio.generate(
                    text,
                    output_path,
                    duration_seconds=duration if isinstance(duration, (int, float)) else None,
                    prompt_influence=influence if isinstance(influence, (int, float)) else None,
                    loop=loop if isinstance(loop, bool) else None,
                )
        return {"jsonrpc": "2.0", "id": request_id, "result": tool_result(result)}
    if request_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "method not found"},
    }


def serve() -> int:
    while True:
        message = read_message()
        if message is None:
            return 0
        response = handle(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    raise SystemExit(serve())
