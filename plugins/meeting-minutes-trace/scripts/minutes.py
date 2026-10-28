"""Write meeting minutes and trace one item back to its official audio time.

The host is AssemblyAI Speech Understanding, pinned in references/contract.md.
A missing API key exits before any socket is opened. This module does not
invent minutes, timestamps, or quotes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

SCHEMA = "meeting-minutes-trace/v1"
STABLE_ID = "proto:market:会议纪要转写"
API_VERSION = "1.3.4"
DEFAULT_BASE = "https://api.assemblyai.com"
ALLOWED_BASES = (
    "https://api.assemblyai.com",
    "https://api.eu.assemblyai.com",
)
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
USER_AGENT = "omnimind-meeting-minutes-trace/0.1.0"


class AdapterError(Exception):
    def __init__(self, status: str, message: str, exit_code: int, **extra: object) -> None:
        super().__init__(message)
        self.payload = {
            "schema": SCHEMA,
            "stableId": STABLE_ID,
            "status": status,
            "message": message,
            **extra,
        }
        self.exit_code = exit_code


class Response:
    def __init__(self, status: int, body: bytes, final_url: str) -> None:
        self.status = status
        self.body = body
        self.final_url = final_url


class Transport:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> Response:
        raise NotImplementedError


class UrllibTransport(Transport):
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(_RejectRedirect())

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> Response:
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise AdapterError(
                        "failed",
                        "AssemblyAI response exceeded 8 MiB and was not parsed.",
                        1,
                        network="response_too_large",
                    )
                return Response(response.status, payload, response.geturl())
        except urllib.error.HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            return Response(exc.code, payload[:MAX_RESPONSE_BYTES], exc.geturl())


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise AdapterError(
            "failed",
            "AssemblyAI redirected the request. The API key was not sent to another host.",
            1,
            network="redirect_refused",
            statusCode=code,
        )


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(error: AdapterError) -> int:
    emit(error.payload)
    return error.exit_code


def base_url(env: dict[str, str]) -> str:
    raw = env.get("ASSEMBLYAI_BASE_URL", "").strip() or DEFAULT_BASE
    normalized = raw.rstrip("/")
    if normalized not in ALLOWED_BASES:
        raise AdapterError(
            "unavailable",
            "ASSEMBLYAI_BASE_URL must be https://api.assemblyai.com or https://api.eu.assemblyai.com.",
            2,
            network="not_sent",
        )
    return normalized


def api_key(env: dict[str, str]) -> str:
    key = env.get("ASSEMBLYAI_API_KEY", "").strip()
    if not key:
        raise AdapterError(
            "unavailable",
            "setup_required: ASSEMBLYAI_API_KEY is not set. No request was sent and no minutes were written.",
            2,
            network="not_sent",
            missing="ASSEMBLYAI_API_KEY",
        )
    return key


def auth_headers(key: str, content_type: str | None = None) -> dict[str, str]:
    headers = {"Authorization": key, "User-Agent": USER_AGENT}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def decode_json(response: Response) -> dict[str, object]:
    try:
        parsed = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(
            "failed",
            "AssemblyAI did not return JSON.",
            1,
            httpStatus=response.status,
            detail=str(exc),
        ) from exc
    if not isinstance(parsed, dict):
        raise AdapterError(
            "failed",
            "AssemblyAI JSON was not an object.",
            1,
            httpStatus=response.status,
        )
    return parsed


def raise_for_status(response: Response, parsed: dict[str, object]) -> None:
    if 200 <= response.status < 300:
        return
    message = parsed.get("error")
    if not isinstance(message, str) or not message.strip():
        message = f"AssemblyAI returned HTTP {response.status}."
    status = "unavailable" if response.status in (401, 403) else "failed"
    code = 2 if response.status in (401, 403) else 1
    raise AdapterError(
        status,
        message,
        code,
        httpStatus=response.status,
        network="sent",
        minutesWritten=False,
    )


def is_time(value: object) -> bool:
    return type(value) is int and value >= 0


def summarization_body(audio_url: str) -> dict[str, object]:
    return {
        "audio_url": audio_url,
        "language_detection": True,
        "speech_understanding": {
            "request": {
                "summarization": {
                    "summary_type": "paragraph",
                }
            }
        },
    }


def action_items_body(audio_url: str) -> dict[str, object]:
    return {
        "audio_url": audio_url,
        "language_detection": True,
        "speaker_labels": True,
        "speech_understanding": {
            "request": {
                "action_items": {
                    "include_decisions": True,
                }
            }
        },
    }


def request_task_names(body: dict[str, object]) -> list[str]:
    understanding = body.get("speech_understanding")
    if not isinstance(understanding, dict):
        return []
    request = understanding.get("request")
    if not isinstance(request, dict):
        return []
    return sorted(str(key) for key in request.keys())


def nested(payload: dict[str, object], *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def parse_summary_items(transcript: dict[str, object]) -> list[dict[str, object]]:
    summarization = nested(
        transcript,
        "speech_understanding",
        "response",
        "summarization",
    )
    if not isinstance(summarization, dict):
        raise AdapterError(
            "failed",
            "Completed transcript has no speech_understanding.response.summarization.",
            1,
            network="sent",
            minutesWritten=False,
        )
    summary = summarization.get("summary")
    if not isinstance(summary, list):
        raise AdapterError(
            "failed",
            "Summarization response has no summary array.",
            1,
            network="sent",
            minutesWritten=False,
        )
    items: list[dict[str, object]] = []
    for index, raw in enumerate(summary, start=1):
        if not isinstance(raw, dict):
            items.append({"id": f"m{index}", "kind": "summary", "traceable": False, "reason": "item_not_object"})
            continue
        text = raw.get("text")
        start = raw.get("start")
        end = raw.get("end")
        traceable = isinstance(text, str) and text.strip() != "" and is_time(start) and is_time(end) and end > start
        item: dict[str, object] = {
            "id": f"m{index}",
            "kind": "summary",
            "traceable": traceable,
            "text": text if isinstance(text, str) else None,
            "headline": raw.get("headline") if isinstance(raw.get("headline"), str) else None,
            "start": start if is_time(start) else None,
            "end": end if is_time(end) else None,
        }
        if not traceable:
            item["reason"] = "missing_official_span_or_text"
        items.append(item)
    return items


def parse_action_items(transcript: dict[str, object]) -> list[dict[str, object]]:
    action_items = nested(transcript, "speech_understanding", "response", "action_items")
    if not isinstance(action_items, dict):
        raise AdapterError(
            "failed",
            "Completed transcript has no speech_understanding.response.action_items.",
            1,
            network="sent",
        )
    raw_items = action_items.get("items")
    if not isinstance(raw_items, list):
        raise AdapterError(
            "failed",
            "Action items response has no items array.",
            1,
            network="sent",
        )
    items: list[dict[str, object]] = []
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            items.append({"id": f"a{index}", "kind": "action", "traceable": False, "reason": "item_not_object"})
            continue
        text = raw.get("action_item")
        timestamp = raw.get("timestamp")
        quote = raw.get("quote")
        traceable = isinstance(text, str) and text.strip() != "" and is_time(timestamp)
        item: dict[str, object] = {
            "id": f"a{index}",
            "kind": "action",
            "traceable": traceable,
            "text": text if isinstance(text, str) else None,
            "quote": quote if isinstance(quote, str) else None,
            "timestamp": timestamp if is_time(timestamp) else None,
        }
        if not traceable:
            item["reason"] = "missing_official_timestamp_or_text"
        items.append(item)
    return items


def overlapping_words(transcript: dict[str, object], start: int, end: int) -> list[dict[str, object]]:
    words = transcript.get("words")
    if not isinstance(words, list):
        return []
    selected: list[dict[str, object]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        word_start = word.get("start")
        word_end = word.get("end")
        text = word.get("text")
        if not (is_time(word_start) and is_time(word_end) and word_end > word_start and isinstance(text, str)):
            continue
        if word_start < end and word_end > start:
            selected.append({"text": text, "start": word_start, "end": word_end})
    return selected


def words_at(transcript: dict[str, object], timestamp: int) -> list[dict[str, object]]:
    words = transcript.get("words")
    if not isinstance(words, list):
        return []
    selected: list[dict[str, object]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        word_start = word.get("start")
        word_end = word.get("end")
        text = word.get("text")
        if not (is_time(word_start) and is_time(word_end) and isinstance(text, str)):
            continue
        if word_start <= timestamp < word_end:
            selected.append({"text": text, "start": word_start, "end": word_end})
    return selected


def empty_document(audio_url: str, host: str, skip_actions: bool) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "stableId": STABLE_ID,
        "apiVersion": API_VERSION,
        "status": "pending",
        "host": host,
        "audioUrl": audio_url,
        "skipActions": skip_actions,
        "minutesJob": None,
        "actionsJob": None,
        "minutes": [],
        "actions": [],
        "nativePass": False,
    }


def write_document(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_document(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("failed", f"Cannot read minutes file: {exc}", 2, network="not_sent") from exc
    if not isinstance(parsed, dict) or parsed.get("schema") != SCHEMA:
        raise AdapterError("failed", "Minutes file is not a meeting-minutes-trace document.", 2, network="not_sent")
    return parsed


def post_json(
    transport: Transport,
    url: str,
    key: str,
    body: dict[str, object],
    timeout: float,
) -> dict[str, object]:
    response = transport.request(
        "POST",
        url,
        auth_headers(key, "application/json"),
        json.dumps(body).encode("utf-8"),
        timeout,
    )
    parsed = decode_json(response)
    raise_for_status(response, parsed)
    return parsed


def get_json(transport: Transport, url: str, key: str, timeout: float) -> dict[str, object]:
    response = transport.request("GET", url, auth_headers(key), None, timeout)
    parsed = decode_json(response)
    raise_for_status(response, parsed)
    return parsed


def upload_file(
    transport: Transport,
    host: str,
    key: str,
    file_path: Path,
    timeout: float,
) -> str:
    if not file_path.is_file():
        raise AdapterError(
            "unavailable",
            "Audio file does not exist. No upload was sent.",
            2,
            network="not_sent",
        )
    response = transport.request(
        "POST",
        f"{host}/v2/upload",
        auth_headers(key, "application/octet-stream"),
        file_path.read_bytes(),
        timeout,
    )
    parsed = decode_json(response)
    raise_for_status(response, parsed)
    upload_url = parsed.get("upload_url")
    if not isinstance(upload_url, str) or not upload_url.startswith("https://"):
        raise AdapterError(
            "failed",
            "Upload response did not include an https upload_url.",
            1,
            network="sent",
        )
    return upload_url


def resolve_audio_url(args: argparse.Namespace, transport: Transport, host: str, key: str) -> str:
    if bool(args.audio_url) == bool(args.audio_file):
        raise AdapterError(
            "unavailable",
            "Pass exactly one of --audio-url or --audio-file.",
            2,
            network="not_sent",
        )
    if args.audio_url:
        if not (args.audio_url.startswith("https://") or args.audio_url.startswith("http://")):
            raise AdapterError(
                "unavailable",
                "audio_url must be an http or https URL.",
                2,
                network="not_sent",
            )
        return args.audio_url
    return upload_file(transport, host, key, Path(args.audio_file), args.timeout)


def submit_transcript(
    transport: Transport,
    host: str,
    key: str,
    body: dict[str, object],
    timeout: float,
) -> str:
    if len(request_task_names(body)) != 1:
        raise AdapterError(
            "failed",
            "Refusing to submit a speech_understanding request that is not exactly one documented task.",
            1,
            network="not_sent",
        )
    parsed = post_json(transport, f"{host}/v2/transcript", key, body, timeout)
    transcript_id = parsed.get("id")
    if not isinstance(transcript_id, str) or not transcript_id:
        raise AdapterError("failed", "Transcript submit did not return an id.", 1, network="sent")
    return transcript_id


def poll_transcript(
    transport: Transport,
    host: str,
    key: str,
    transcript_id: str,
    timeout: float,
    wait_seconds: float,
    interval_seconds: float,
    sleep: Callable[[float], None],
    now: Callable[[], float],
) -> dict[str, object]:
    deadline = now() + wait_seconds
    last: dict[str, object] | None = None
    while True:
        last = get_json(transport, f"{host}/v2/transcript/{transcript_id}", key, timeout)
        status = last.get("status")
        if status in ("completed", "error"):
            return last
        if now() >= deadline:
            return last
        sleep(min(interval_seconds, max(0.0, deadline - now())))


def job_from_transcript(transcript: dict[str, object], transcript_id: str) -> dict[str, object]:
    status = transcript.get("status")
    job: dict[str, object] = {
        "transcriptId": transcript_id,
        "status": status if isinstance(status, str) else "unknown",
    }
    error = transcript.get("error")
    if isinstance(error, str) and error:
        job["error"] = error
    return job


def apply_minutes(document: dict[str, object], transcript: dict[str, object], transcript_id: str) -> None:
    document["minutesJob"] = job_from_transcript(transcript, transcript_id)
    if transcript.get("status") == "completed":
        items = parse_summary_items(transcript)
        for item in items:
            if item.get("traceable") is True:
                item["audioWords"] = overlapping_words(transcript, item["start"], item["end"])
        document["minutes"] = items
    elif transcript.get("status") == "error":
        raise AdapterError(
            "failed",
            str(transcript.get("error") or "Summarization transcript failed."),
            1,
            network="sent",
            transcriptId=transcript_id,
        )


def apply_actions(document: dict[str, object], transcript: dict[str, object], transcript_id: str) -> None:
    document["actionsJob"] = job_from_transcript(transcript, transcript_id)
    if transcript.get("status") == "completed":
        items = parse_action_items(transcript)
        for item in items:
            if item.get("traceable") is True:
                item["audioWords"] = words_at(transcript, item["timestamp"])
        document["actions"] = items
    elif transcript.get("status") == "error":
        document["actionsError"] = str(transcript.get("error") or "Action items transcript failed.")


def refresh_status(document: dict[str, object]) -> str:
    minutes_job = document.get("minutesJob")
    actions_job = document.get("actionsJob")
    minutes_status = minutes_job.get("status") if isinstance(minutes_job, dict) else None
    if minutes_status != "completed":
        document["status"] = "pending" if minutes_status in ("queued", "processing") else "failed"
        return str(document["status"])
    if document.get("skipActions") is True:
        document["status"] = "completed"
        return "completed"
    actions_status = actions_job.get("status") if isinstance(actions_job, dict) else None
    if actions_status == "completed":
        document["status"] = "completed"
    elif actions_status in ("queued", "processing") or actions_job is None:
        document["status"] = "pending"
    else:
        document["status"] = "completed_minutes_actions_failed"
    return str(document["status"])


def trace_item(document: dict[str, object], item_id: str) -> dict[str, object]:
    pools = (
        document.get("minutes") if item_id.startswith("m") else document.get("actions"),
    )
    items = pools[0]
    if not isinstance(items, list):
        items = []
    found = next((item for item in items if isinstance(item, dict) and item.get("id") == item_id), None)
    if found is None:
        raise AdapterError(
            "not_found",
            f"No minute item {item_id}.",
            4,
            network="not_sent",
        )
    if found.get("traceable") is not True:
        raise AdapterError(
            "untraceable",
            f"{item_id} has no official audio time in the saved transcript.",
            4,
            network="not_sent",
            item=found,
        )
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "stableId": STABLE_ID,
        "status": "traced",
        "network": "not_sent",
        "id": item_id,
        "kind": found.get("kind"),
        "text": found.get("text"),
        "nativePass": False,
    }
    if found.get("kind") == "summary":
        payload["audioSpan"] = {
            "start": found.get("start"),
            "end": found.get("end"),
            "unit": "official_integer_timestamp",
            "source": "speech_understanding.response.summarization.summary",
        }
        payload["headline"] = found.get("headline")
    else:
        payload["audioSpan"] = {
            "timestamp": found.get("timestamp"),
            "unit": "official_integer_timestamp",
            "source": "speech_understanding.response.action_items.items",
        }
        payload["quote"] = found.get("quote")
    if isinstance(found.get("audioWords"), list):
        payload["audioWords"] = found["audioWords"]
    audio_url = document.get("audioUrl")
    if isinstance(audio_url, str):
        payload["audioUrl"] = audio_url
    return payload


def run_write(
    args: argparse.Namespace,
    env: dict[str, str],
    transport: Transport,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict[str, object]:
    key = api_key(env)
    host = base_url(env)
    out = Path(args.out)
    if out.exists() and not args.force:
        raise AdapterError(
            "unavailable",
            "Output file already exists. Pass --force to replace it, or use resume.",
            2,
            network="not_sent",
        )
    audio_url = resolve_audio_url(args, transport, host, key)
    document = empty_document(audio_url, host, args.skip_actions)
    write_document(out, document)
    try:
        minutes_id = submit_transcript(transport, host, key, summarization_body(audio_url), args.timeout)
        document["minutesJob"] = {"transcriptId": minutes_id, "status": "submitted"}
        write_document(out, document)
        minutes = poll_transcript(
            transport,
            host,
            key,
            minutes_id,
            args.timeout,
            args.wait_seconds,
            args.interval_seconds,
            sleep,
            now,
        )
        apply_minutes(document, minutes, minutes_id)
        write_document(out, document)
        if not args.skip_actions and minutes.get("status") == "completed":
            actions_id = submit_transcript(transport, host, key, action_items_body(audio_url), args.timeout)
            document["actionsJob"] = {"transcriptId": actions_id, "status": "submitted"}
            write_document(out, document)
            actions = poll_transcript(
                transport,
                host,
                key,
                actions_id,
                args.timeout,
                args.wait_seconds,
                args.interval_seconds,
                sleep,
                now,
            )
            apply_actions(document, actions, actions_id)
        status = refresh_status(document)
        document["nativePass"] = False
        write_document(out, document)
    except AdapterError as exc:
        document["status"] = exc.payload["status"]
        document["nativePass"] = False
        document["lastError"] = exc.payload["message"]
        write_document(out, document)
        raise
    if status == "pending":
        raise AdapterError(
            "pending",
            "Official transcript is not completed. Resume with the saved transcript id. No minutes were invented.",
            3,
            network="sent",
            out=str(out),
            documentStatus=status,
        )
    if status == "failed":
        raise AdapterError(
            "failed",
            "Summarization transcript did not complete.",
            1,
            network="sent",
            out=str(out),
        )
    return document


def run_resume(
    args: argparse.Namespace,
    env: dict[str, str],
    transport: Transport,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict[str, object]:
    key = api_key(env)
    host = base_url(env)
    path = Path(args.minutes)
    document = read_document(path)
    saved_host = document.get("host")
    if saved_host != host:
        raise AdapterError(
            "unavailable",
            "Minutes file host does not match ASSEMBLYAI_BASE_URL. No new request was sent.",
            2,
            network="not_sent",
        )
    for label, apply in (("minutesJob", apply_minutes), ("actionsJob", apply_actions)):
        job = document.get(label)
        if not isinstance(job, dict):
            continue
        if job.get("status") in ("completed", "error"):
            continue
        transcript_id = job.get("transcriptId")
        if not isinstance(transcript_id, str) or not transcript_id:
            continue
        transcript = poll_transcript(
            transport,
            host,
            key,
            transcript_id,
            args.timeout,
            args.wait_seconds,
            args.interval_seconds,
            sleep,
            now,
        )
        apply(document, transcript, transcript_id)
        write_document(path, document)
    status = refresh_status(document)
    document["nativePass"] = False
    write_document(path, document)
    if status == "pending":
        raise AdapterError(
            "pending",
            "Official transcript is still not completed.",
            3,
            network="sent",
            documentStatus=status,
        )
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe meeting minutes and trace one item to its audio time.")
    sub = parser.add_subparsers(dest="command", required=True)

    write = sub.add_parser("write")
    write.add_argument("--audio-url")
    write.add_argument("--audio-file")
    write.add_argument("--out", required=True)
    write.add_argument("--skip-actions", action="store_true")
    write.add_argument("--force", action="store_true")
    write.add_argument("--wait-seconds", type=float, default=20)
    write.add_argument("--timeout", type=float, default=30)
    write.add_argument("--interval-seconds", type=float, default=3)

    resume = sub.add_parser("resume")
    resume.add_argument("--minutes", required=True)
    resume.add_argument("--wait-seconds", type=float, default=20)
    resume.add_argument("--timeout", type=float, default=30)
    resume.add_argument("--interval-seconds", type=float, default=3)

    trace = sub.add_parser("trace")
    trace.add_argument("--minutes", required=True)
    trace.add_argument("--id", required=True)

    sub.add_parser("doctor")
    return parser


def main(argv: list[str] | None = None, env: dict[str, str] | None = None, transport: Transport | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    environment = env if env is not None else dict(os.environ)
    try:
        if args.command == "doctor":
            api_key(environment)
            base_url(environment)
            emit(
                {
                    "schema": SCHEMA,
                    "stableId": STABLE_ID,
                    "status": "configured",
                    "key": "present",
                    "network": "not_sent",
                    "nativePass": False,
                }
            )
            return 0
        if args.command == "trace":
            emit(trace_item(read_document(Path(args.minutes)), args.id))
            return 0
        client = transport if transport is not None else UrllibTransport()
        if args.command == "write":
            emit(run_write(args, environment, client))
            return 0
        emit(run_resume(args, environment, client))
        return 0
    except AdapterError as exc:
        return fail(exc)


if __name__ == "__main__":
    raise SystemExit(main())
