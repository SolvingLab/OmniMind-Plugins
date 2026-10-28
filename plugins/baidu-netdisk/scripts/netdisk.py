"""Command entry for the 百度网盘 cloud file adapter.

Reads only the BAIDU_NETDISK_* variables named in the skill. It does not
search the home directory or any copied connection file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from baidu_netdisk import (
    Config,
    UrllibTransport,
    authorize_url,
    config_from_env,
    delete_path,
    device_code,
    device_token,
    download_fsid,
    exchange_code,
    file_meta,
    list_dir,
    make_dir,
    move_or_copy,
    probe_host,
    probe_sse,
    quota,
    refresh_token,
    rename_path,
    search,
    status,
    stream_download,
    uinfo,
    upload_file,
)


def emit(exit_code: int, payload: dict) -> int:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    sys.stdout.buffer.write(encoded)
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="百度网盘 cloud file adapter. Missing token does not contact the account.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("quota")
    sub.add_parser("uinfo")
    sub.add_parser("probe-host")
    auth = sub.add_parser("authorize-url")
    auth.add_argument("--mode", choices=("code", "official-mcp"), default="official-mcp")
    exchange = sub.add_parser("exchange-code")
    exchange.add_argument("--code", required=True)
    sub.add_parser("refresh-token")
    sub.add_parser("device-code")
    device = sub.add_parser("device-token")
    device.add_argument("--device-code", required=True)
    listed = sub.add_parser("list")
    listed.add_argument("--dir", default="/")
    listed.add_argument("--start", type=int, default=0)
    listed.add_argument("--limit", type=int, default=100)
    listed.add_argument("--order", default="name")
    listed.add_argument("--desc", type=int, default=0)
    found = sub.add_parser("search")
    found.add_argument("--key", required=True)
    found.add_argument("--dir", default="/")
    found.add_argument("--category", type=int)
    found.add_argument("--recursion", action="store_true")
    meta = sub.add_parser("meta")
    meta.add_argument("--path", default="")
    meta.add_argument("--fsid", default="")
    meta.add_argument("--dlink", action="store_true")
    mkdir = sub.add_parser("mkdir")
    mkdir.add_argument("--path", required=True)
    mkdir.add_argument("--yes", action="store_true")
    renamed = sub.add_parser("rename")
    renamed.add_argument("--path", required=True)
    renamed.add_argument("--newname", required=True)
    renamed.add_argument("--yes", action="store_true")
    for name in ("move", "copy"):
        command = sub.add_parser(name)
        command.add_argument("--path", required=True)
        command.add_argument("--dest", required=True)
        command.add_argument("--newname", required=True)
        command.add_argument("--yes", action="store_true")
    deleted = sub.add_parser("delete")
    deleted.add_argument("--path", required=True)
    deleted.add_argument("--yes", action="store_true")
    uploaded = sub.add_parser("upload")
    uploaded.add_argument("--local", required=True)
    uploaded.add_argument("--path", required=True)
    uploaded.add_argument("--uploadid", default="")
    uploaded.add_argument("--yes", action="store_true")
    downloaded = sub.add_parser("download")
    downloaded.add_argument("--fsid", required=True)
    downloaded.add_argument("--output", required=True)
    downloaded.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None, env: dict | None = None, transport=None) -> int:
    args = build_parser().parse_args(argv)
    current_env = os.environ if env is None else env
    config: Config = config_from_env(current_env)
    client = transport or UrllibTransport().exchange
    if args.command == "status":
        result = status(config, client)
    elif args.command == "quota":
        result = quota(config, client)
    elif args.command == "uinfo":
        result = uinfo(config, client)
    elif args.command == "probe-host":
        result = probe_host(client, probe_sse)
    elif args.command == "authorize-url":
        result = authorize_url(config, args.mode)
    elif args.command == "exchange-code":
        result = exchange_code(config, args.code, client)
    elif args.command == "refresh-token":
        result = refresh_token(config, client)
    elif args.command == "device-code":
        result = device_code(config, client)
    elif args.command == "device-token":
        result = device_token(config, args.device_code, client)
    elif args.command == "list":
        result = list_dir(config, client, args.dir, args.start, args.limit, args.order, args.desc)
    elif args.command == "search":
        result = search(config, client, args.key, args.dir, args.category, args.recursion)
    elif args.command == "meta":
        result = file_meta(config, client, args.path, args.fsid, args.dlink)
    elif args.command == "mkdir":
        result = make_dir(config, client, args.path, args.yes)
    elif args.command == "rename":
        result = rename_path(config, client, args.path, args.newname, args.yes)
    elif args.command == "move":
        result = move_or_copy(config, client, "move", args.path, args.dest, args.newname, args.yes)
    elif args.command == "copy":
        result = move_or_copy(config, client, "copy", args.path, args.dest, args.newname, args.yes)
    elif args.command == "delete":
        result = delete_path(config, client, args.path, args.yes)
    elif args.command == "upload":
        local = Path(args.local)
        if not local.is_file():
            return emit(
                2,
                {
                    "ok": False,
                    "state": "unavailable",
                    "reason": "invalid_argument",
                    "product": "百度网盘",
                    "detail": "upload --local must be an existing file",
                    "upstreamCalled": False,
                },
            )
        result = upload_file(
            config,
            client,
            str(local),
            args.path,
            None,
            args.yes,
            resume_uploadid=args.uploadid,
        )
    elif args.command == "download":
        output = Path(args.output)
        if output.exists():
            return emit(
                2,
                {
                    "ok": False,
                    "state": "unavailable",
                    "reason": "invalid_argument",
                    "product": "百度网盘",
                    "detail": "download output already exists; this adapter does not overwrite it",
                    "upstreamCalled": False,
                },
            )
        result = download_fsid(config, client, args.fsid, stream_download if transport is None else _reject_live_stream, args.output, args.yes)
    else:
        return emit(2, {"ok": False, "state": "unavailable", "reason": "invalid_argument", "product": "百度网盘"})
    return emit(result.exit_code, result.payload)


def _reject_live_stream(request, output: str) -> int:
    raise RuntimeError("injected transport cannot stream a live dlink; unit tests cover download separately")


if __name__ == "__main__":
    raise SystemExit(main())
