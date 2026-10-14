"""Pick which synced camera angle to show for each bar of a DJ-set clip (Creative Studio).

Two or more camera files, already synced to the set (offsets from your cross-correlation),
and the bar grid (from serato_set_grid.py or a beat tracker) go in. For every bar and angle
it measures what an editor checks at a glance: sharpness (variance of the Laplacian),
exposure (how far mean brightness is from a usable middle), motion energy, and strobe
flashes; optional extra scores (hands up from pose, a learned taste score) can be added per
bar. Then it chooses the angle per bar with dynamic programming under the rules club edits
follow: cut only on bar lines, hold each shot between a minimum and maximum number of bars
(take both from your reference-clip measurements), pay a cost for every cut,
and show the crowd angle for the bar after the drop. Output: a cut list, and a plan JSON for
plan_to_filmcraft.py.

    python shot_picker.py --angle dj=cam_dj.mp4:0.0 --angle crowd=cam_crowd.mp4:-1.42 \\
        --bars bars.txt --drop 1846.2 --crowd crowd --start 1838.0 --end 1854.0 --out plan.json

`--angle name=file:offset` means set time t is at t + offset seconds in that file.
bars.txt: one bar start time (set seconds) per line.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass

import cv2
import numpy as np

W, H, FPS = 320, 180, 10  # analysis resolution and rate


@dataclass
class Angle:
    name: str
    path: str
    offset: float  # file time = set time + offset


def decode_gray(path: str, start: float, dur: float) -> np.ndarray:
    """Gray frames (n, H, W) float32 in 0..1 at FPS, from file time `start`."""
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{max(start, 0):.3f}", "-t", f"{dur:.3f}", "-i", path,
           "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (W * H)
    return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.float32) / 255.0


def bar_features(frames: np.ndarray) -> dict:
    if len(frames) == 0:
        return {"sharp": 0.0, "exposure": 0.0, "motion": 0.0, "strobe": 1.0}
    sharp = float(np.mean([cv2.Laplacian(f, cv2.CV_32F).var() for f in frames]))
    mean = frames.mean(axis=(1, 2))
    exposure = float(1.0 - min(abs(float(np.median(mean)) - 0.45) / 0.45, 1.0))
    motion = float(np.abs(np.diff(frames, axis=0)).mean()) if len(frames) > 1 else 0.0
    # a strobe is a brightness spike that comes back: up (or down) a lot, then back next frame
    spikes = 0
    for i in range(1, len(mean) - 1):
        if abs(mean[i] - mean[i - 1]) > 0.2 and abs(mean[i] - mean[i + 1]) > 0.2:
            spikes += 1
    return {"sharp": sharp, "exposure": exposure, "motion": motion, "strobe": spikes / max(len(mean), 1)}


def scores(feats: dict, extra: dict | None = None, weights: dict | None = None) -> dict:
    """feats[(angle, bar)] -> score; features normalised across all angles and bars."""
    w = {"sharp": 0.45, "exposure": 0.35, "motion": 0.20, "strobe": -0.6, **(weights or {})}
    keys = list(feats)
    out = {k: 0.0 for k in keys}
    for f in ("sharp", "motion"):
        v = np.array([feats[k][f] for k in keys])
        lo, hi = np.percentile(v, 5), np.percentile(v, 95)
        norm = np.clip((v - lo) / (hi - lo), 0, 1) if hi > lo else np.zeros_like(v)
        for k, x in zip(keys, norm):
            out[k] += w[f] * float(x)
    for k in keys:
        out[k] += w["exposure"] * feats[k]["exposure"] + w["strobe"] * feats[k]["strobe"]
        if extra and k in extra:
            out[k] += extra[k]
    return out


def choose(names: list[str], n_bars: int, score: dict, min_bars: int = 2, cut_cost: float = 0.15,
           forced: dict[int, str] | None = None, max_bars: int | None = None,
           long_cost: float = 0.2) -> list[str]:
    """Angle per bar maximising total score minus cut_cost per cut, every shot at least min_bars
    long (the last may be shorter), forced[bar] = angle honoured. max_bars is soft: each bar
    beyond it costs long_cost, so a shot runs long only when the other angles are worse (a hard
    cap would cut to an out-of-focus angle just to obey it). Viterbi over (angle, shot length)."""
    forced = forced or {}
    R = n_bars
    soft = max_bars or n_bars
    neg = -1e9
    A = len(names)
    best = np.full((n_bars, A, R + 1), neg)
    back = np.zeros((n_bars, A, R + 1, 2), dtype=int)
    for a, name in enumerate(names):
        if forced.get(0, name) == name:
            best[0, a, 1] = score[(name, 0)]
    for b in range(1, n_bars):
        for a, name in enumerate(names):
            if forced.get(b, name) != name:
                continue
            s = score[(name, b)]
            for r in range(2, R + 1):  # stay on the same angle: the shot grows by a bar
                gain = s - (long_cost if r > soft else 0.0)
                if best[b - 1, a, r - 1] + gain > best[b, a, r]:
                    best[b, a, r] = best[b - 1, a, r - 1] + gain
                    back[b, a, r] = (a, r - 1)
            for pa in range(A):  # cut from another angle whose shot is long enough
                if pa == a:
                    continue
                for pr in range(min_bars, R + 1):
                    if best[b - 1, pa, pr] - cut_cost + s > best[b, a, 1]:
                        best[b, a, 1] = best[b - 1, pa, pr] - cut_cost + s
                        back[b, a, 1] = (pa, pr)
    a, r = np.unravel_index(np.argmax(best[n_bars - 1]), best[n_bars - 1].shape)
    if best[n_bars - 1, a, r] <= neg / 2:
        raise ValueError("no edit satisfies the constraints (forced bars vs min/max shot length?)")
    path = []
    for b in range(n_bars - 1, -1, -1):
        path.append(names[a])
        a, r = back[b, a, r]
    return path[::-1]


def to_cuts(path: list[str], bars: list[float], end: float) -> list[dict]:
    cuts, i = [], 0
    while i < len(path):
        j = i
        while j + 1 < len(path) and path[j + 1] == path[i]:
            j += 1
        t0, t1 = bars[i], bars[j + 1] if j + 1 < len(bars) else end
        cuts.append({"angle": path[i], "start": t0, "end": t1, "bars": j - i + 1})
        i = j + 1
    return cuts


def pick(angles: list[Angle], bars: list[float], end: float, drop: float | None = None, crowd: str | None = None,
         min_bars: int = 2, cut_cost: float = 0.15, extra: dict | None = None, max_bars: int | None = 4) -> dict:
    n = len(bars)
    feats = {}
    for ang in angles:
        frames = decode_gray(ang.path, bars[0] + ang.offset, end - bars[0])
        for b in range(n):
            t0 = bars[b] - bars[0]
            t1 = (bars[b + 1] if b + 1 < n else end) - bars[0]
            feats[(ang.name, b)] = bar_features(frames[int(t0 * FPS): int(t1 * FPS)])
    sc = scores(feats, extra)
    forced = {}
    if drop is not None and crowd:
        db = max(i for i, t in enumerate(bars) if t <= drop + 1e-6)
        for b in (db, db + 1):  # crowd reaction lags the drop by about a bar
            if b < n:
                forced[b] = crowd
    path = choose([a.name for a in angles], n, sc, min_bars, cut_cost, forced, max_bars)
    return {"path": path, "cuts": to_cuts(path, bars, end), "features": {f"{k[0]}:{k[1]}": v for k, v in feats.items()}}


def to_plan(result: dict, angles: list[Angle], audio: str | None = None, audio_offset: float = 0.0) -> dict:
    off = {a.name: a for a in angles}
    plan = {"width": 1080, "height": 1920, "fps": 30, "sources": {a.name: a.path for a in angles},
            "cuts": [{"source": c["angle"], "in": round(c["start"] + off[c["angle"]].offset, 3),
                      "duration": round(c["end"] - c["start"], 3)} for c in result["cuts"]]}
    if audio:
        plan["audio"] = {"path": audio, "offset": result["cuts"][0]["start"] + audio_offset}
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--angle", action="append", required=True, help="name=file:offset")
    ap.add_argument("--bars", required=True)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--drop", type=float)
    ap.add_argument("--crowd")
    ap.add_argument("--min-bars", type=int, default=2)
    ap.add_argument("--max-bars", type=int, default=4, help="longest shot; take it from your reference-clip medians")
    ap.add_argument("--cut-cost", type=float, default=0.15)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    angles = []
    for spec in args.angle:
        name, rest = spec.split("=", 1)
        path, _, off = rest.rpartition(":")
        angles.append(Angle(name, path, float(off)))
    bars = [float(x) for x in open(args.bars, encoding="utf-8") if x.strip()]
    bars = [b for b in bars if (args.start is None or b >= args.start) and b < args.end]
    res = pick(angles, bars, args.end, args.drop, args.crowd, args.min_bars, args.cut_cost, max_bars=args.max_bars)
    for c in res["cuts"]:
        print(f'{c["start"]:9.2f}–{c["end"]:9.2f}  {c["angle"]:<8} {c["bars"]} bar(s)')
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(to_plan(res, angles), fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
