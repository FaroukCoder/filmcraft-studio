"""Checks dj_guard.py with a stand-in "DJ app" (a sleeping Python process whose name
we watch) and a fake llama-swap that records unload calls.

    python test_dj_guard.py
"""
from __future__ import annotations

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


class FakeSwap(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        calls.append(self.path)
        self.send_response(200)
        self.end_headers()

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

    # 1) app running -> DJ mode on, unload called, lock written, gpu not allowed
    dj_guard.main(common + ["--max-loops", "2"])
    if "/api/models/unload" not in calls:
        problems.append(f"unload not called: {calls}")
    if dj_guard.gpu_allowed():
        problems.append("gpu_allowed() should be False in DJ mode")

    # 2) watch a name nothing has -> after the grace period, DJ mode off, lock removed
    calls.clear()
    dj_guard.main(["--llama-swap", url, "--interval", "0.2", "--grace", "0.5", "--dry-run",
                   "--watch", "definitely-not-running-*", "--max-loops", "6"])
    # DEFAULT_WATCH patterns (Serato/Ableton) are not running in a test container
    if not dj_guard.gpu_allowed():
        problems.append("gpu_allowed() should be True after the apps exit")
    srv.shutdown()
    dj_guard.LOCK.unlink(missing_ok=True)
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
