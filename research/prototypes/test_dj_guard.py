"""Checks dj_guard.py with a stand-in "DJ app" (this Python process, whose name we watch)
and a fake llama-swap that records calls: the "dj" profile is switched on, everything is
unloaded, a model that sneaks in while you play is unloaded again, and the profile is
cleared when the apps exit. test_dj_guard_llama_swap.py runs the same against the real
llama-swap binary.

    python test_dj_guard.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

os.environ["GPU_DJ_LOCK"] = str(Path(tempfile.gettempdir()) / "test_gpu_dj_mode.lock")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dj_guard  # noqa: E402

calls: list[str] = []
sneaky = {"running": []}  # what GET /running reports next


class FakeSwap(BaseHTTPRequestHandler):
    def _reply(self, body: dict | None = None):
        data = json.dumps(body or {}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):  # noqa: N802
        calls.append(f"POST {self.path}")
        if self.path == "/api/models/unload":
            sneaky["running"] = []
        self._reply()

    def do_PUT(self):  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        calls.append(f"PUT {self.path} {self.rfile.read(n).decode()}")
        self._reply()

    def do_GET(self):  # noqa: N802
        self._reply({"running": [{"model": m} for m in sneaky["running"]]})

    def log_message(self, *a):
        pass


def main() -> int:
    problems = []
    dj_guard.LOCK.unlink(missing_ok=True)
    srv = HTTPServer(("127.0.0.1", 0), FakeSwap)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"
    me = Path(sys.executable).name  # the stand-in app is another python process
    common = ["--llama-swap", url, "--watch", me, "--interval", "0.2", "--grace", "0.5", "--dry-run",
              "--stop", "echo stop", "--start", "echo start"]

    # 1) app running -> profile "dj" on, unload called, lock written, gpu not allowed
    dj_guard.main(common + ["--max-loops", "2"])
    if not any(c.startswith("PUT /api/profiles/active") and '"dj"' in c for c in calls):
        problems.append(f"dj profile not activated: {calls}")
    if "POST /api/models/unload" not in calls:
        problems.append(f"unload not called: {calls}")
    if dj_guard.gpu_allowed():
        problems.append("gpu_allowed() should be False in DJ mode")

    # 1b) still playing, and something got loaded anyway -> unloaded again
    calls.clear()
    sneaky["running"] = ["comfyui_auto"]
    dj_guard.main(common + ["--max-loops", "2"])
    if "POST /api/models/unload" not in calls or sneaky["running"]:
        problems.append(f"model loaded during DJ mode was not unloaded again: {calls}")

    # 2) watch a name nothing has -> after the grace period, DJ mode off, lock removed
    calls.clear()
    dj_guard.main(["--llama-swap", url, "--interval", "0.2", "--grace", "0.5", "--dry-run",
                   "--watch", "definitely-not-running-*", "--max-loops", "6"])
    # DEFAULT_WATCH patterns (Serato/Ableton) are not running in a test container
    if not dj_guard.gpu_allowed():
        problems.append("gpu_allowed() should be True after the apps exit")
    if not any(c.startswith("PUT /api/profiles/active") and "null" in c for c in calls):
        problems.append(f"profile not cleared on leaving DJ mode: {calls}")
    srv.shutdown()
    dj_guard.LOCK.unlink(missing_ok=True)
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
