"""Camera <-> recording sync on a REAL DJ set: python -m studio.test_sync
Test media (local only, never posted): E:/AI/studio-jobs/_testmedia/public/sara_landry_boiler_room.mp4
(a public Boiler Room set). The "camera" is a stretch of the set heard through a simulated phone
mic: 150 Hz high-pass, ~3.7 kHz low-pass, room reverb, AGC-style compression, noise.
Every match must be sample-exact (5 ms) with confidence >= SYNC_MIN_CONF, in a normal room (direct
sound 2x the room) and a wet one (room 9x the direct); a camera from another recording must stay
below the gate. (Synthetic loops can't test this: they repeat sample-exactly, real sets don't.)"""
import glob
import sys
from pathlib import Path

import numpy as np

from studio import dj

SET = Path(r"E:\AI\studio-jobs\_testmedia\public\sara_landry_boiler_room.mp4")
if not SET.exists():
    sys.exit(f"skipped: no test set at {SET}")
sr = dj.SR
full = dj.load_audio(SET)
rng = np.random.default_rng(42)
tail = rng.standard_normal(int(0.5 * sr)) * np.exp(-np.arange(int(0.5 * sr)) / (0.12 * sr))
tail[: int(0.01 * sr)] = 0
tail /= np.sqrt((tail ** 2).sum())


def phone(x: np.ndarray, room: float) -> np.ndarray:
    """`room` = room-to-direct amplitude ratio (0.7 normal, 3 = very wet)."""
    ir = tail * room
    ir[0] = 1.0
    x = x - np.convolve(x, np.ones(70) / 70, mode="same")
    x = np.convolve(np.convolve(x, np.ones(3) / 3, mode="same"), ir, mode="full")[: len(x)]
    return np.tanh(4 * x) * 0.3 + rng.standard_normal(len(x)) * 0.01


for k in range(6):
    dur = float(rng.uniform(60, 300))
    shift = round(float(rng.uniform(30, len(full) / sr - dur - 30)), 3)
    seg = full[int(shift * sr): int((shift + dur) * sr)]
    for room in (0.7, 3.0):
        off, conf = dj.sync_offset(full, phone(seg, room))
        print(f"truth {shift:8.3f} ({dur:5.1f} s, room {room}): {off - shift:+.4f} s, confidence {conf}")
        assert abs(off - shift) <= 0.005 and conf >= dj.SYNC_MIN_CONF, (shift, room, off, conf)

others = [f for f in sorted(glob.glob(r"E:\AI\reels\media\*\video.mp4"))[:40:8]]
for f in others:  # unrelated audio must not pass the gate
    y = dj.load_audio(Path(f))
    if len(y) >= 30 * sr:
        off, conf = dj.sync_offset(full, y)
        print(f"other recording {Path(f).parent.name}: confidence {conf}")
        assert conf < dj.SYNC_MIN_CONF, (f, conf)
print("ok")
