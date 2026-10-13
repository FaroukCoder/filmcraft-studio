"""One door to an LLM for the edit planner and the judge (master plan ④/⑨, Q7/Q21).

    ask(prompt, schema, images=[...], provider="local" | "claude") -> {"data", "provider", "model"}

- local: Ollama. Text goes to the coder model, images to the vision model. It runs under the
  shared GPU lock and waits while Serato/Ableton is open (`yield_to_music`).
- claude: Claude Code headless (`claude -p`, the owner's subscription), no GPU. Images are
  handed over as file paths the CLI may Read.
Both decode against the JSON schema, so the caller gets a dict, never prose. STUDIO_LLM picks the
default provider; every result says which model decided, and that goes into the job report."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import urllib.request
from pathlib import Path

PROVIDER = os.environ.get("STUDIO_LLM", "local")
OLLAMA = "http://127.0.0.1:11434"
TEXT_MODEL, VISION_MODEL = "coder-stable:latest", "qwen3-vl:8b"
CLAUDE = os.environ.get("CLAUDE_CLI", "claude")


class LLMError(RuntimeError):
    pass


def _engine():
    """The shared GPU lock lives in the generation engine (stdlib only, loaded by path)."""
    spec = importlib.util.spec_from_file_location("qwen_engine", r"E:\AI\qwen-image-mcp\server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check(data: dict, schema: dict) -> dict:
    missing = [k for k in schema.get("required", []) if k not in data]
    if missing:
        raise LLMError(f"answer is missing {missing}")
    return data


def _local(prompt: str, schema: dict, images: list[Path]) -> tuple[dict, str]:
    model = VISION_MODEL if images else TEXT_MODEL
    msg = {"role": "user", "content": prompt}
    if images:
        msg["images"] = [base64.b64encode(Path(p).read_bytes()).decode() for p in images]
    body = json.dumps({"model": model, "stream": False, "think": False, "format": schema, "keep_alive": 0,
                       "options": {"temperature": 0.3, "num_ctx": 16384, "num_predict": 4096},
                       "messages": [msg]}).encode()
    eng = _engine()
    with eng.gpu_job(on_wait=lambda: print("studio: waiting for the GPU (another job, or Serato/Ableton open)"),
                     yield_to_music=True):
        req = urllib.request.Request(f"{OLLAMA}/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1800) as r:
            resp = json.loads(r.read())
    try:
        return json.loads(resp["message"]["content"]), model
    except (KeyError, ValueError) as exc:
        raise LLMError(f"{model} gave no valid JSON ({resp.get('done_reason')}): {exc}") from exc


def _claude(prompt: str, schema: dict, images: list[Path]) -> tuple[dict, str]:
    args = [CLAUDE, "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(schema),
            "--no-session-persistence"]
    if images:  # the CLI reads the image files itself
        args += ["--allowedTools", "Read"] + [x for p in {str(Path(i).parent) for i in images}
                                              for x in ("--add-dir", p)]
        args[2] += "\n\nImages (read each one before answering):\n" + "\n".join(str(i) for i in images)
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    try:
        out = json.loads(r.stdout)
    except ValueError as exc:
        raise LLMError(f"claude -p printed no JSON (exit {r.returncode}): {r.stderr[-400:] or r.stdout[-400:]}") from exc
    if out.get("is_error"):
        raise LLMError(f"claude -p: {out.get('result')}")  # e.g. "Not logged in · Please run /login"
    data = out.get("structured_output")
    if data is None:
        data = json.loads(out["result"])
    return data, "claude:" + (",".join(out.get("modelUsage", {})) or "default")


def ask(prompt: str, schema: dict, images: list[Path] | None = None, provider: str | None = None) -> dict:
    provider = provider or PROVIDER
    fn = {"local": _local, "claude": _claude}[provider]
    data, model = fn(prompt, schema, list(images or []))
    return {"data": _check(data, schema), "provider": provider, "model": model}
