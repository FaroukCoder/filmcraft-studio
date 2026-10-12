"""DJ analysis on synthetic techno with known drops (whatstheID's generator): python -m studio.test_dj"""
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\Administrator\Desktop\whatstheID\backend\tests")
from synth_techno import render  # noqa: E402

from studio import dj  # noqa: E402

# a "set": three tracks back to back, every drop's time known to the sample
y, truth, t = [], [], 0.0
for seed in (3, 7, 11):
    a, info = render(seed)
    for name in ("drop", "drop 2"):
        if name in info["cues"]:
            truth.append(round(t + info["cues"][name], 2))
    y.append(a)
    t += len(a) / dj.SR
mix = np.concatenate(y)
print(f"set: {t / 60:.1f} min, true drops at {truth}")

found = dj.find_drops(mix)
hits = [d for d in truth if any(abs(f["time"] - d) <= 1.0 for f in found)]
false = [f for f in found if all(abs(f["time"] - d) > 1.0 for d in truth)]
print(f"found {len(found)} drops: {[f['time'] for f in found]}")
assert len(hits) == len(truth), f"missed drops: {set(truth) - set(hits)}"
assert len(false) <= 1, f"false drops: {false}"

# sync: the camera's room mic hears the set late, quieter, muffled and noisy
rng = np.random.default_rng(0)
shift = 37.3  # camera started recording 37.3 s into the set
cam = mix[int(shift * dj.SR): int((shift + 180) * dj.SR)] * 0.4
cam = np.convolve(cam, np.ones(6) / 6, mode="same") + rng.standard_normal(len(cam)) * 0.02
off, conf = dj.sync_offset(mix[: int(400 * dj.SR)], cam)
print(f"sync offset {off}s (true {shift}), confidence {conf}")
assert abs(off - shift) < 0.005 and conf > 8, (off, conf)

# moments: drop clips start before the drop (build-up) and land on the bar grid
m = dj.moments(mix)
assert all(x["start"] < x["at"] < x["end"] for x in m)
bpm_ok = [x for x in m if x["bpm"] and 118 <= x["bpm"] <= 150]
assert len(bpm_ok) == len(m)
print("ok")

# every detected drop has a real breakdown before it, so a non-zero tension score
assert all(f["break"] >= 6 and f["score"] > 0 for f in found), found
print("ok")
