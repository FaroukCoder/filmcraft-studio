"""The DJ guard against a real llama-swap binary and the committed llama-swap.example.yaml.

Each model's command is swapped for a tiny stand-in HTTP server (no GPU, no model files);
everything else in the config (the exclusive group, the routes, the "dj" profile) is used
as written. Checks: asking for one model unloads the other (one GPU owner); the guard's
"DJ mode" makes llama-swap refuse models (404) and empties it; a ComfyUI job that sneaks in
through /comfyui/ (which ignores profiles) is unloaded again; leaving DJ mode restores
service. Needs the llama-swap binary (env LLAMA_SWAP_BIN or on PATH); prints SKIP without.

    python test_dj_guard_llama_swap.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent
STAND_IN = """import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
name, port = sys.argv[1], int(sys.argv[2])
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _ok(self):
        n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
        b = json.dumps({"served_by": name, "choices": [{"message": {"content": name}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    do_GET = do_POST = _ok
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    exe = os.environ.get("LLAMA_SWAP_BIN") or shutil.which("llama-swap")
    if not exe:
        print("SKIP  needs the llama-swap binary (set LLAMA_SWAP_BIN)")
        return 0
    problems = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "stand_in.py").write_text(STAND_IN, encoding="utf-8")
        cfg = yaml.safe_load((HERE / "llama-swap.example.yaml").read_text(encoding="utf-8"))
        for k in cfg["models"]:
            cfg["models"][k]["cmd"] = f'"{sys.executable}" "{d / "stand_in.py"}" {k} ${{PORT}}'
        (d / "cfg.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        swap = subprocess.Popen([exe, "-config", str(d / "cfg.yaml"), "-listen", f"127.0.0.1:{port}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        lock = d / "dj.lock"
        env = dict(os.environ, GPU_DJ_LOCK=str(lock))
        app = None
        try:
            for _ in range(50):
                try:
                    httpx.get(f"{base}/health", timeout=1)
                    break
                except httpx.HTTPError:
                    time.sleep(0.1)

            def chat(model: str) -> int:
                return httpx.post(f"{base}/v1/chat/completions", json={"model": model, "messages": []}, timeout=30).status_code

            def loaded() -> list[str]:
                return [m["model"] for m in httpx.get(f"{base}/running", timeout=5).json()["running"]]

            chat("agent")
            chat("vlm")
            if loaded() != ["vlm"]:
                problems.append(f"exclusive group: expected only vlm loaded, got {loaded()}")

            # a stand-in "Serato": a copy of python with the right name, sleeping
            fake = d / ("Serato DJ Pro.exe" if os.name == "nt" else "Serato DJ Pro")
            shutil.copy(sys.executable, fake)
            app = subprocess.Popen([str(fake), "-c", "import time; time.sleep(60)"])
            time.sleep(0.5)
            guard = [sys.executable, str(HERE / "dj_guard.py"), "--llama-swap", base, "--interval", "0.3", "--grace", "0.5"]
            subprocess.run(guard + ["--max-loops", "2"], env=env, capture_output=True, text=True, timeout=60)
            if loaded():
                problems.append(f"DJ mode on, but still loaded: {loaded()}")
            if chat("agent") != 404:
                problems.append("DJ mode on, but llama-swap still serves the agent model")
            httpx.get(f"{base}/comfyui/", timeout=30)  # a ComfyUI job sneaking in
            subprocess.run(guard + ["--max-loops", "2"], env=env, capture_output=True, text=True, timeout=60)
            if loaded():
                problems.append(f"model loaded during DJ mode was not unloaded: {loaded()}")

            app.terminate()
            app.wait(10)
            subprocess.run(guard + ["--max-loops", "6"], env=env, capture_output=True, text=True, timeout=60)
            if lock.exists():
                problems.append("lock still present after the DJ app exited")
            if chat("agent") != 200:
                problems.append("after DJ mode, llama-swap does not serve the agent model again")
        finally:
            if app and app.poll() is None:
                app.kill()
            swap.terminate()
            try:
                swap.wait(10)
            except subprocess.TimeoutExpired:
                swap.kill()
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
