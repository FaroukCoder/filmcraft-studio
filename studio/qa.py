"""Post-render QA (after OpenMontage's self-review): a render is checked before anyone sees it.
One ffmpeg pass: black frames, frozen picture, dead air, true peak; ffprobe: size, fps, length
against the EDL; the caption style against Instagram's UI overlay. Problems make `ok` false and
are listed in the version's report; the render is kept either way (nothing is overwritten)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

BLACK_S, FREEZE_S, SILENCE_S = 0.5, 2.0, 1.5
MAX_TRUE_PEAK = -1.0  # dBTP: platforms re-encode, hotter peaks clip
IG_BOTTOM_UI = 0.20   # share of the frame height the Reels caption/buttons overlay covers


def probe(render: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json",
                          str(render)], capture_output=True, text=True).stdout
    j = json.loads(out or "{}")
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), None)
    a = any(s["codec_type"] == "audio" for s in j.get("streams", []))
    fps = None
    if v:
        n, d = v["r_frame_rate"].split("/")
        fps = round(float(n) / float(d or 1), 3)
    return {"size": [v["width"], v["height"]] if v else None, "fps": fps, "audio": a,
            "duration": float(j.get("format", {}).get("duration", 0) or 0)}


def scan(render: Path) -> str:
    """ffmpeg's detector log for the whole render (stderr)."""
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(render),
         "-vf", f"blackdetect=d={BLACK_S}:pix_th=0.10,freezedetect=n=0.003:d={FREEZE_S}",
         "-af", f"silencedetect=n=-50dB:d={SILENCE_S},ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


def parse(log: str) -> dict:
    """Spans (start, end) per detector plus the true peak, from an ffmpeg detector log."""
    black = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    fs, fe = re.findall(r"freeze_start: ([\d.]+)", log), re.findall(r"freeze_end: ([\d.]+)", log)
    ss, se = re.findall(r"silence_start: (-?[\d.]+)", log), re.findall(r"silence_end: ([\d.]+)", log)
    peaks = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", log)
    return {"black": black,
            "freeze": [(float(a), float(b) if b else None) for a, b in zip(fs, fe + [None] * len(fs))],
            "silence": [(max(0.0, float(a)), float(b) if b else None) for a, b in
                        zip(ss, se + [None] * len(ss))],
            "true_peak": float(peaks[-1]) if peaks and peaks[-1] != "-inf" else None}


def check(render: Path, edl: dict, expected_seconds: float | None = None) -> dict:
    problems: list[str] = []
    p = probe(render)
    if p["size"] != list(edl.get("size", [1080, 1920])):
        problems.append(f"size {p['size']} != {edl.get('size')}")
    if p["fps"] and abs(p["fps"] - edl.get("fps", 30)) > 0.01:
        problems.append(f"fps {p['fps']} != {edl.get('fps')}")
    if not p["audio"]:
        problems.append("no audio stream")
    if expected_seconds and abs(p["duration"] - expected_seconds) > 2 / edl.get("fps", 30) + 0.05:
        problems.append(f"length {p['duration']:.2f}s, the EDL says {expected_seconds:.2f}s")
    d = parse(scan(render))
    for kind in ("black", "freeze", "silence"):
        for a, b in d[kind]:
            problems.append(f"{kind} {a:.1f}-{b:.1f}s" if b is not None else f"{kind} from {a:.1f}s to the end")
    if d["true_peak"] is not None and d["true_peak"] > MAX_TRUE_PEAK:
        problems.append(f"true peak {d['true_peak']} dBTP (> {MAX_TRUE_PEAK})")
    cs = edl.get("caption_style") or {}
    if edl.get("captions") and cs.get("anchor") == "bottom" and cs.get("margin", 0) < IG_BOTTOM_UI:
        problems.append(f"captions sit under the Reels UI (bottom margin {cs.get('margin')} < {IG_BOTTOM_UI})")
    return {"ok": not problems, "problems": problems, **p, "true_peak": d["true_peak"]}
