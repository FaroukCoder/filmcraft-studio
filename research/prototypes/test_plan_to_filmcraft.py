"""End-to-end check of plan_to_filmcraft.py against a real filmcraft-cli build.

Two synthetic cameras (a "DJ" shot with a pink subject sweeping across the frame, a static
"crowd" shot), a set recording and an Arabic/English caption file go in; the plan cuts
DJ / crowd / DJ / crowd and asks for a reframe from noisy, gappy subject detections.
Checks: 1080x1920, the right length, cuts on the planned frames, the subject kept near
the vertical frame's safe zone on reframed shots (vs a centre-crop baseline), audio present, captions burned in.

Needs ffmpeg and a filmcraft-cli built from the fork (env FILMCRAFT_CLI, or the repo's
target/release); prints SKIP without one.

    python test_plan_to_filmcraft.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_to_filmcraft as p2f  # noqa: E402

W, H, FPS = 1920, 1080, 30
BOX_W, BOX_H = 160, 320


def subject_x(t: float) -> float:
    """Left edge of the pink box in dj.mp4 at source time t (same formula as the ffmpeg overlay)."""
    return 300 + 1200 * (0.5 - 0.5 * np.cos(2 * np.pi * t / 12))


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def make_fixtures(d: Path) -> None:
    ff("-f", "lavfi", "-i", f"color=c=0x202030:s={W}x{H}:r={FPS}:d=12", "-f", "lavfi", "-i", f"color=c=0xff2080:s={BOX_W}x{BOX_H}:r={FPS}:d=12",
       "-filter_complex", "[0][1]overlay=x='300+1200*(0.5-0.5*cos(2*PI*t/12))':y=380", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "dj.mp4"))
    ff("-f", "lavfi", "-i", f"color=c=0x103020:s={W}x{H}:r={FPS}:d=12", "-f", "lavfi", "-i", f"color=c=0x20ff80:s={BOX_W}x{BOX_H}:r={FPS}:d=12",
       "-filter_complex", "[0][1]overlay=x=880:y=380", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "crowd.mp4"))
    ff("-f", "lavfi", "-i", "sine=frequency=110:duration=12", "-ar", "48000", str(d / "set.wav"))
    (d / "ids.srt").write_text("1\n00:00:00,300 --> 00:00:02,500\nالحفلة بدأت — ID: Artist – Track\n\n", encoding="utf-8")


def frames(path: Path, w: int, h: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(int)


def find_cli() -> str | None:
    for c in (os.environ.get("FILMCRAFT_CLI"), str(HERE.parents[1] / "target" / "release" / "filmcraft-cli"), shutil.which("filmcraft-cli")):
        if c and Path(c).exists():
            return c
    return None


def main() -> int:
    cli = find_cli()
    if not cli or not shutil.which("ffmpeg"):
        print("SKIP  needs ffmpeg and a filmcraft-cli build (set FILMCRAFT_CLI)")
        return 0
    rng = np.random.default_rng(1)
    problems = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        make_fixtures(d)

        def detections(start: float, dur: float) -> list:
            out = []
            for t in np.arange(start, start + dur, 0.1):
                miss = rng.random() < 0.15
                out.append([round(float(t), 2), None if miss else round(float(subject_x(t) + BOX_W / 2 + rng.normal(0, 20)), 1)])
            return out

        cuts = [
            {"source": "dj", "in": 1.0, "duration": 3.0, "subject_x": detections(1.0, 3.0), "subject_width": BOX_W},
            {"source": "crowd", "in": 4.0, "duration": 1.5},
            {"source": "dj", "in": 6.0, "duration": 3.0, "subject_x": detections(6.0, 3.0), "subject_width": BOX_W},
            {"source": "crowd", "in": 9.0, "duration": 1.5},
        ]
        plan = {"name": "test", "width": 1080, "height": 1920, "fps": FPS,
                "sources": {"dj": str(d / "dj.mp4"), "crowd": str(d / "crowd.mp4")},
                "audio": {"path": str(d / "set.wav"), "offset": 1.0},
                "cuts": cuts,
                "captions": {"srt": str(d / "ids.srt"), "size": 56},
                "export": {"path": str(d / "out.mp4"), "crf": 20}}
        rep = p2f.build(plan, cli)
        out = d / "out.mp4"

        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,nb_frames",
                                          "-of", "json", str(out)], capture_output=True, text=True, check=True).stdout)["streams"]
        v = next(s for s in info if s["codec_type"] == "video")
        if (v["width"], v["height"]) != (1080, 1920):
            problems.append(f"size {v['width']}x{v['height']}")
        if not any(s["codec_type"] == "audio" for s in info):
            problems.append("no audio stream")

        f = frames(out, 270, 480)  # quarter size
        n = len(f)
        if abs(n - 9 * FPS) > 1:
            problems.append(f"{n} frames, expected {9 * FPS}")
        bg = f[:, 5:40, 5:40].reshape(n, -1, 3).mean(1)  # top-left corner: background colour
        is_dj = bg[:, 2] > bg[:, 1]  # dj bg is blue-ish (0x202030), crowd bg green-ish (0x103020)
        cut_frames = list(np.nonzero(np.diff(is_dj.astype(int)))[0] + 1)
        want = [90, 135, 225]
        if len(cut_frames) != 3 or any(abs(a - b) > 1 for a, b in zip(cut_frames, want)):
            problems.append(f"cuts at frames {cut_frames}, expected {want}")

        pink = (f[..., 0] > 180) & (f[..., 1] < 110) & (f[..., 2] > 70)
        dj_frames = [i for i in range(n) if is_dj[i]]
        counts = np.array([pink[i].sum() for i in dj_frames])
        full = np.percentile(counts, 90)  # pixel count of the whole, unclipped subject
        visible = counts >= 0.9 * full
        offs = [abs(np.nonzero(pink[i])[1].mean() * 4 - 540) for i in dj_frames if pink[i].sum() > 50]
        scale = 1920 / H
        safe = (1080 / scale / 2 - (BOX_W / 2 + 20)) * scale  # the L1 path's safe zone, in output pixels
        if visible.mean() < 0.98:
            problems.append(f"subject fully in frame on only {visible.mean():.0%} of reframed frames")
        if offs and np.percentile(offs, 95) > safe + 25:
            problems.append(f"subject leaves the safe zone: 95th pct offset {np.percentile(offs, 95):.0f} px > {safe:.0f}")
        # baseline: a centre crop (no reframe) of the same shots
        crop_lo, crop_hi = W / 2 - 1080 / scale / 2, W / 2 + 1080 / scale / 2
        src_t = np.concatenate([1.0 + np.arange(90) / FPS, 6.0 + np.arange(90) / FPS])
        bx = subject_x(src_t)
        centre_crop_visible = float(np.mean((bx >= crop_lo) & (bx + BOX_W <= crop_hi)))
        kf = [c["keyframes"] for c in rep["cuts"] if c["source"] == "dj"]
        if not kf or max(kf) >= 90 or min(kf) < 2:
            problems.append(f"keyframes per reframed shot {kf} (expected a few, not one per frame)")

        low = f[:, 300:470, :, :]  # bottom third, where captions sit
        white = ((low > 225).all(-1)).sum((1, 2))
        if not (white[30] > 40 and white[240] < 5):
            problems.append(f"captions: white px at 1.0 s {white[30]}, at 8.0 s {white[240]}")

        print(json.dumps({"frames": n, "cuts": [int(c) for c in cut_frames], "keyframes": kf,
                          "subject_fully_visible": round(float(visible.mean()), 3),
                          "centre_crop_baseline_visible": round(centre_crop_visible, 3),
                          "centre_offset_px_median": round(float(np.median(offs)), 1) if offs else None,
                          "centre_offset_px_p95": round(float(np.percentile(offs, 95)), 1) if offs else None,
                          "safe_zone_px": round(float(safe), 1),
                          "caption_white_px": [int(white[30]), int(white[240])]}))
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
