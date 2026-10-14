"""Checks vlm_json_guard.py against a fake model server (no GPU, no model download).

The fake server answers like a misbehaving VLM: the first request gets a looping
answer, the second gets invalid JSON, the third (the two-pass notes call) gets plain
text, and the fourth (the formatting call) gets valid JSON. It also checks frame
downscaling and the token budget guard.

    python test_vlm_json_guard.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vlm_json_guard as g  # noqa: E402

VALID = {
    "summary": "A reel showing a local agent setup.",
    "takeaways": ["Run the model behind one server", "Cap the frames"],
    "tools": [{"name": "llama-swap", "kind": "open_source", "url_or_repo_seen": "mostlygeek/llama-swap"}],
    "topics": ["local llm"],
    "language": "en",
}
ANSWERS = [
    '{"summary": "' + "the tool the tool the tool the tool " * 20 + '"',  # loops
    '{"summary": "ok", "takeaways": ["a","b","c","d","e","f","g"], "tools": [], "topics": [], "language": "en"}',  # 7 > 5
    "Notes: shows llama-swap; advice to cap frames.",
    json.dumps(VALID),
]
seen: list[dict] = []


class Fake(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        seen.append(body)
        answer = ANSWERS[min(len(seen) - 1, len(ANSWERS) - 1)]
        if self.path == "/api/chat":
            out = {"message": {"content": answer}}
        else:
            out = {"choices": [{"message": {"content": answer}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def make_video(path: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=1080x1920:r=25:d=4",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


def main() -> int:
    problems = []
    # llama.cpp's schema-to-grammar converter skips nested $refs silently: the schema sent must have none
    schema_text = json.dumps(g.bounded_schema())
    if "$ref" in schema_text or "$defs" in schema_text:
        problems.append("bounded_schema() still contains $ref/$defs")
    tool_kind = g.bounded_schema()["properties"]["tools"]["items"]["properties"]["kind"]
    if "enum" not in tool_kind or g.bounded_schema()["properties"]["tools"].get("maxItems") != 8:
        problems.append(f"inlined schema lost its enum or maxItems: {tool_kind}")
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "reel.mp4"
        make_video(video)
        frames = g.extract_frames(video, 8)
        sizes = {(w, h) for _, w, h in frames}
        if sizes != {(360, 640)}:
            problems.append(f"frames not downscaled to 360x640: {sizes}")
        tokens = g.estimate_tokens(frames, "x" * 300)
        if not 1700 < tokens < 2100:
            problems.append(f"token estimate {tokens} (expected ~1.9k for 8 frames at 360x640)")
        full_res = [(b"", 1080, 1920)] * 8
        if g.estimate_tokens(full_res, "") < 16000:
            problems.append("full-resolution estimate should exceed 16k tokens")

        srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        for api in ("ollama", "openai"):
            seen.clear()
            args = Namespace(api=api, url=f"http://127.0.0.1:{srv.server_port}", model="m", frames=8,
                             num_ctx=8192, max_tokens=700, max_context_chars=6000, timeout=10.0)
            note, log = g.note_for(None, "transcript here", args, frames=frames)
            steps = [l.get("attempt") + (":ok" if l.get("ok") else ":" + str(l.get("error", ""))[:20]) for l in log]
            print(api, steps)
            if note is None or note.tools[0].name != "llama-swap":
                problems.append(f"{api}: expected a valid note after fallback, got {log}")
            if len(seen) != 4:
                problems.append(f"{api}: expected 4 requests, saw {len(seen)}")
            first = seen[0]
            opts = first.get("options", first)
            if opts.get("presence_penalty") != 1.5 or opts.get("temperature") != 0.7:
                problems.append(f"{api}: sampling not set: {opts}")
            if api == "ollama" and (first.get("format", {}).get("properties", {}).get("takeaways", {}).get("maxItems") != 5):
                problems.append("ollama: schema missing maxItems")
            if len(seen[1].get("messages")[0].get("images", [])) not in (0, 4) and api == "ollama":
                problems.append("ollama: retry did not halve frames")

        # budget guard: a tiny num_ctx must skip both image attempts without calling the server
        seen.clear()
        args = Namespace(api="ollama", url=f"http://127.0.0.1:{srv.server_port}", model="m", frames=8,
                         num_ctx=1000, max_tokens=700, max_context_chars=6000, timeout=10.0)
        _, log = g.note_for(None, "", args, frames=frames)
        if not all("skipped" in l for l in log[:2]):
            problems.append(f"budget guard did not skip: {log}")
        srv.shutdown()
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
