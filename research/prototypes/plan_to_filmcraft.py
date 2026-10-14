"""Turn an edit plan (JSON) into a finished vertical clip with your FilmCraft fork, headless.

This is the seam between Creative Studio's planner and FilmCraft: the planner (an LLM, or
rules from the reference-clip measurements) writes a small JSON plan; this script drives
`filmcraft-cli mcp` (stdio JSON-RPC, no window) to build the sequence and export it.

    python plan_to_filmcraft.py plan.json --cli C:\\ai\\filmcraft\\filmcraft-cli.exe

plan.json:
{
  "name": "geeza-0412-drop",
  "width": 1080, "height": 1920, "fps": 30,
  "sources": {"dj": "D:/night/cam_dj.mp4", "crowd": "D:/night/cam_crowd.mp4"},
  "audio": {"path": "D:/night/serato_rec.wav", "offset": 1830.0},
  "cuts": [
    {"source": "dj", "in": 1830.0, "duration": 3.2,
     "subject_x": [[1830.0, 812], [1830.5, 840], [1831.0, null], ...]},
    {"source": "crowd", "in": 1833.1, "duration": 1.6}
  ],
  "captions": {"srt": "D:/night/ids.srt", "font": "Noto Sans Arabic", "size": 56},
  "export": {"path": "D:/out/geeza-0412-drop.mp4", "crf": 20, "loudness_lufs": -14}
}

- `in` / `offset` are seconds in the source file; cuts are laid end to end from 0.
- `subject_x` (optional): subject centre in source pixels over source time (null = not found),
  with `subject_width` (source px; default a third of the crop) so the whole subject stays in,
  e.g. rtmlib body centres or YuNet faces. It is smoothed into an L1-optimal camera path
  (`l1_reframe_path.py`) and written as Motion anchor keyframes at the path's corners,
  so FilmCraft pans like an operator: holds, constant pans, short eases. Without it the
  shot is centre-cropped.
- How it maps onto FilmCraft (found by testing the fork, October 2026): Motion `scale`
  fills the frame; Motion `anchor` is in source pixels and `position` in sequence pixels,
  so a reframe is "anchor.x = crop centre" keyframed over time, created with
  `effects.setParam {"keyframe": true, "time": <sequence ticks>}`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from l1_reframe_path import l1_path  # noqa: E402

TICKS = 254_016_000_000  # FilmCraft ticks per second


class FilmCraftError(RuntimeError):
    pass


class FilmCraft:
    """Minimal MCP client for `filmcraft-cli mcp` (JSON-RPC 2.0, one message per line)."""

    def __init__(self, cli: str, project: str | None = None):
        cmd = [cli, "mcp"] + (["--project", project] if project else [])
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.n = 0
        self._ask("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "creative-studio", "version": "0"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg: dict) -> None:
        if self.p.stdin is None:
            raise FilmCraftError("filmcraft-cli stdin closed")
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def _ask(self, method: str, params: dict) -> dict:
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        while True:
            line = self.p.stdout.readline() if self.p.stdout else ""
            if not line:
                raise FilmCraftError(f"filmcraft-cli exited during {method}")
            msg = json.loads(line)
            if msg.get("id") == self.n:  # skip progress notifications
                if "error" in msg:
                    raise FilmCraftError(f"{method}: {msg['error']}")
                return msg["result"]

    def run(self, command: str, params: dict | None = None):
        r = self._ask("tools/call", {"name": "command_run", "arguments": {"id": command, "params": params or {}}})
        text = r["content"][0]["text"] if r.get("content") else ""
        if r.get("isError"):
            raise FilmCraftError(f"{command}: {text}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def close(self) -> None:
        try:
            if self.p.stdin:
                self.p.stdin.close()
            self.p.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()


def probe_size(cli: str, path: str) -> tuple[int, int]:
    out = subprocess.run([cli, "probe", path], capture_output=True, text=True, check=True).stdout
    v = json.loads(out)["video"]
    return int(v["width"]), int(v["height"])


def knots(path: np.ndarray, tol: float = 3.0) -> list[int]:
    """Keyframe frames for a per-frame path: Douglas-Peucker simplification, so linear
    interpolation between the returned frames stays within `tol` source pixels of the path.
    An L1 path is mostly holds and straight pans, so it needs only a handful; a curved path
    gets as many as its curvature needs. (Keeping only frames where the slope jumps, the
    first version, kept two keyframes for a smooth curve and the subject left the frame.)"""
    n = len(path)
    if n <= 2:
        return list(range(n))
    keep = {0, n - 1}
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = np.arange(a + 1, b)
        line = path[a] + (path[b] - path[a]) * (seg - a) / (b - a)
        err = np.abs(path[seg] - line)
        k = int(np.argmax(err))
        if err[k] > tol:
            m = int(seg[k])
            keep.add(m)
            stack += [(a, m), (m, b)]
    return sorted(keep)


def camera_path(samples: list, start: float, duration: float, fps: float,
                src_w: int, crop_w: float, subject_w: float | None = None) -> np.ndarray:
    """Per-frame crop centre (source px) from sparse (time, x|None) samples."""
    n = max(int(round(duration * fps)), 1)
    t = start + np.arange(n) / fps
    pts = [(float(a), float(b)) for a, b in samples if b is not None]
    if not pts:
        return np.full(n, src_w / 2.0)
    ts, xs = np.array(pts).T
    x = np.interp(t, ts, xs)
    x[(t < ts.min() - 0.5) | (t > ts.max() + 0.5)] = np.nan  # no extrapolation far out
    missing = {round(float(a) * fps) for a, b in samples if b is None}
    for i, ti in enumerate(t):
        if round(ti * fps) in missing:
            x[i] = np.nan
    # The L1 path keeps the subject's CENTRE inside the safe zone, so the margin must cover
    # half the subject's width or a wide subject (a DJ's body) pokes out of the frame.
    sw = subject_w if subject_w else crop_w / 3
    margin = min(sw / 2 + 20, crop_w / 2 - 1)
    return l1_path(x, frame_w=src_w, crop_w=crop_w, margin=margin)


def build(plan: dict, cli: str) -> dict:
    w, h, fps = int(plan.get("width", 1080)), int(plan.get("height", 1920)), float(plan.get("fps", 30))
    fc = FilmCraft(cli)
    report = {"cuts": []}
    try:
        fc.run("file.newSequence", {"name": plan.get("name", "clip"), "width": w, "height": h, "fps": fps})
        names = list(plan["sources"])
        paths = [str(Path(plan["sources"][k]).resolve()) for k in names]
        items = dict(zip(names, fc.run("file.import", {"paths": paths})["items"]))
        sizes = {k: probe_size(cli, p) for k, p in zip(names, paths)}

        at = 0.0
        for cut in plan["cuts"]:
            src = cut["source"]
            sw, sh = sizes[src]
            dur = float(cut["duration"])
            clip = fc.run("timeline.place", {
                "item": items[src], "track": "V1", "time": round(at * TICKS), "insert": False,
                "sourceIn": round(float(cut["in"]) * TICKS), "duration": round(dur * TICKS), "audio": False,
            })["clips"][0]
            scale = max(w / sw, h / sh)  # fill the vertical frame
            fc.run("effects.setParam", {"clip": clip, "effect": "motion", "param": "scale", "value": round(scale * 100, 3)})
            entry = {"clip": clip, "source": src, "at": at, "duration": dur, "keyframes": 0}
            if cut.get("subject_x"):
                crop_w = w / scale  # crop width in source pixels
                path = camera_path(cut["subject_x"], float(cut["in"]), dur, fps, sw, crop_w, cut.get("subject_width"))
                ks = knots(path)
                for i in ks:
                    fc.run("effects.setParam", {
                        "clip": clip, "effect": "motion", "param": "anchor", "keyframe": True,
                        "time": round((at + i / fps) * TICKS), "value": [round(float(path[i]), 1), sh / 2],
                    })
                entry.update(keyframes=len(ks), path_min=float(path.min()), path_max=float(path.max()))
            report["cuts"].append(entry)
            at += dur

        if plan.get("audio"):
            a = plan["audio"]
            aitem = fc.run("file.import", {"paths": [str(Path(a["path"]).resolve())]})["items"][0]
            fc.run("timeline.place", {"item": aitem, "track": "A1", "time": 0, "insert": False, "video": False,
                                      "sourceIn": round(float(a.get("offset", 0)) * TICKS), "duration": round(at * TICKS)})

        cap = plan.get("captions")
        if cap:
            fc.run("file.import", {"paths": [str(Path(cap["srt"]).resolve())]})
            style = {"track": "C1"}
            for k in ("font", "size"):
                if cap.get(k) is not None:
                    style[k] = cap[k]
            if len(style) > 1:
                fc.run("captions.setStyle", style)

        ex = plan.get("export", {})
        params = {"path": str(Path(ex.get("path", "out.mp4")).resolve()), "format": "h264", "width": w, "height": h,
                  "range": "custom", "startSeconds": 0, "endSeconds": at, "bitrateMode": "crf",
                  "crf": int(ex.get("crf", 20)), "audio": bool(plan.get("audio")), "burnCaptions": bool(cap), "wait": True}
        if ex.get("loudness_lufs") is not None:
            params["loudnessLufs"] = float(ex["loudness_lufs"])
        report["export"] = fc.run("file.exportMedia", params)
        report["duration"] = at
        return report
    finally:
        fc.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("plan", type=Path)
    ap.add_argument("--cli", default="filmcraft-cli", help="path to filmcraft-cli built from your fork")
    args = ap.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    print(json.dumps(build(plan, args.cli), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
