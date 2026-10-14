"""Checks l1_reframe_path.py on a synthetic DJ: sways around x=700 for 10 s, walks to
x=1300 over 2 s, sways there; detections jitter by 15 px and 10 % are missing.
Compares with the usual exponential-moving-average follow.

    python test_l1_reframe_path.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from l1_reframe_path import describe, l1_path  # noqa: E402

FPS, FRAME_W, CROP_W, MARGIN = 30, 1920, 608, 60


def subject(n: int, rng) -> np.ndarray:
    t = np.arange(n) / FPS
    x = np.where(t < 10, 700, np.where(t < 12, 700 + (t - 10) / 2 * 600, 1300)).astype(float)
    x += 25 * np.sin(2 * np.pi * 0.5 * t)  # swaying to the beat
    obs = x + rng.normal(0, 15, n)  # detector jitter
    obs[rng.random(n) < 0.10] = np.nan  # missed detections
    return x, obs


def ema(obs: np.ndarray, alpha: float = 0.15) -> np.ndarray:
    out, cur = np.empty_like(obs), np.nanmean(obs[:10])
    for i, v in enumerate(obs):
        if not np.isnan(v):
            cur = alpha * v + (1 - alpha) * cur
        out[i] = cur
    return np.clip(out, CROP_W / 2, FRAME_W - CROP_W / 2)


def main() -> int:
    rng = np.random.default_rng(3)
    n = 20 * FPS
    truth, obs = subject(n, rng)
    t0 = time.time()
    path = l1_path(obs, FRAME_W, CROP_W, MARGIN)
    secs = time.time() - t0
    d_l1, d_ema = describe(path), describe(ema(obs))
    inside = np.abs(path - truth) <= CROP_W / 2 - 10  # true subject stays in frame (10 px slack)
    print(f"solve {secs:.2f}s for {n} frames")
    print("L1 :", d_l1, f"subject in frame {100 * inside.mean():.1f}%")
    print("EMA:", d_ema)
    problems = []
    if inside.mean() < 0.99:
        problems.append("subject left the crop")
    if d_l1["static_pct"] < 60:
        problems.append(f"L1 path should mostly hold still, static {d_l1['static_pct']}%")
    if d_l1["direction_changes"] > 6:
        problems.append(f"L1 path wobbles: {d_l1['direction_changes']} direction changes")
    if d_l1["direction_changes"] >= d_ema["direction_changes"]:
        problems.append("L1 should wobble less than EMA")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
