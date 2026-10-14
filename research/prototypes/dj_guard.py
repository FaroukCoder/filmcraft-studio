"""Keep the GPU quiet while you DJ or produce (Top 10 #6).

Polls for Serato or Ableton. When one starts: unloads every model behind llama-swap
(POST /api/models/unload), optionally frees ComfyUI (POST /api/free), runs your stop
commands (e.g. stop the llama-swap service) and writes a lock file. When they have
all exited: runs your start commands and removes the lock. Batch jobs call
`gpu_allowed()` before taking work, so they pause instead of fighting your set.

    python dj_guard.py --llama-swap http://127.0.0.1:8080 \
        --stop "sc stop llama-swap" --start "sc start llama-swap"
    python dj_guard.py --once      # print the current state and exit

Windows process names it watches by default: Serato DJ Pro.exe, Serato DJ Lite.exe,
Serato DJ.exe, Ableton Live*.exe (any edition). Add more with --watch.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import psutil

DEFAULT_WATCH = ["Serato DJ Pro*", "Serato DJ Lite*", "Serato DJ.exe", "Ableton Live*"]
LOCK = Path(os.environ.get("GPU_DJ_LOCK", Path(tempfile.gettempdir()) / "gpu_dj_mode.lock"))


def gpu_allowed() -> bool:
    """For batch jobs: False while a DJ or DAW session is running."""
    return not LOCK.exists()


def running(patterns: list[str]) -> list[str]:
    found = set()
    for p in psutil.process_iter(["name"]):
        name = p.info.get("name") or ""
        if any(fnmatch.fnmatch(name.lower(), pat.lower()) for pat in patterns):
            found.add(name)
    return sorted(found)


def _post(url: str, body: dict | None = None) -> str:
    try:
        r = httpx.post(url, json=body or {}, timeout=10)
        return f"{url} -> {r.status_code}"
    except httpx.HTTPError as e:
        return f"{url} -> {type(e).__name__}"


def _run(cmds: list[str], dry: bool) -> list[str]:
    out = []
    for c in cmds:
        if dry:
            out.append(f"(dry) {c}")
            continue
        args = shlex.split(c, posix=(os.name != "nt"))
        res = subprocess.run(args, capture_output=True, text=True)
        out.append(f"{c} -> {res.returncode}")
    return out


def enter_dj_mode(args, apps: list[str]) -> list[str]:
    log = []
    if args.llama_swap:
        log.append(_post(f"{args.llama_swap}/api/models/unload"))
    if args.comfyui:
        log.append(_post(f"{args.comfyui}/api/free", {"unload_models": True, "free_memory": True}))
    log += _run(args.stop, args.dry_run)
    LOCK.write_text(json.dumps({"since": time.time(), "apps": apps}), encoding="utf-8")
    return log


def leave_dj_mode(args) -> list[str]:
    log = _run(args.start, args.dry_run)
    LOCK.unlink(missing_ok=True)
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--watch", action="append", default=[], help="extra process-name pattern")
    ap.add_argument("--llama-swap", help="base URL of llama-swap, e.g. http://127.0.0.1:8080")
    ap.add_argument("--comfyui", help="base URL of a ComfyUI that runs outside llama-swap")
    ap.add_argument("--stop", action="append", default=[], help="command to run on entering DJ mode")
    ap.add_argument("--start", action="append", default=[], help="command to run on leaving DJ mode")
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--grace", type=float, default=20.0, help="seconds the apps must be gone before resuming")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-loops", type=int, default=0, help="for tests: stop after N polls")
    args = ap.parse_args(argv)
    patterns = DEFAULT_WATCH + args.watch

    if args.once:
        print(json.dumps({"dj_apps": running(patterns), "gpu_allowed": gpu_allowed()}))
        return 0
    in_dj, gone_since, loops = LOCK.exists(), None, 0
    while True:
        apps = running(patterns)
        if apps and not in_dj:
            print(f"DJ mode on ({', '.join(apps)}):", *enter_dj_mode(args, apps), sep="\n  ", flush=True)
            in_dj, gone_since = True, None
        elif not apps and in_dj:
            gone_since = gone_since or time.time()
            if time.time() - gone_since >= args.grace:
                print("DJ mode off:", *leave_dj_mode(args), sep="\n  ", flush=True)
                in_dj, gone_since = False, None
        elif apps:
            gone_since = None
        loops += 1
        if args.max_loops and loops >= args.max_loops:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
