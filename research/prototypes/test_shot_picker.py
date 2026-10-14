"""Checks shot_picker.py on two synthetic, offset camera angles at 150 BPM (1.6 s bars):
the DJ angle goes dark for bars 8-11, the crowd angle is out of focus for bars 0-5, the drop
lands on bar 14. A good edit avoids both bad stretches, shows the crowd for the drop bar and
the one after, holds shots two to four bars where both angles are usable, and maps each cut back to the right
time in each file. A strobe check runs on synthetic frames.

    python test_shot_picker.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot_picker as sp  # noqa: E402

BAR = 1.6
N = 18
CROWD_OFFSET = 0.5  # crowd file time = set time + 0.5 s


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def main() -> int:
    problems = []
    end = N * BAR
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        dark0, dark1 = 8 * BAR, 12 * BAR
        ff("-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=25:duration={end:.1f}",
           "-vf", f"eq=brightness=-0.45:enable='between(t,{dark0},{dark1 - 0.05})'", "-pix_fmt", "yuv420p", str(d / "dj.mp4"))
        blur1 = 6 * BAR + CROWD_OFFSET
        ff("-f", "lavfi", "-i", f"testsrc=size=640x360:rate=25:duration={end + CROWD_OFFSET:.1f}",
           "-vf", f"boxblur=12:enable='between(t,0,{blur1 - 0.05})'", "-pix_fmt", "yuv420p", str(d / "crowd.mp4"))
        angles = [sp.Angle("dj", str(d / "dj.mp4"), 0.0), sp.Angle("crowd", str(d / "crowd.mp4"), CROWD_OFFSET)]
        bars = [i * BAR for i in range(N)]
        res = sp.pick(angles, bars, end, drop=14 * BAR + 0.1, crowd="crowd", min_bars=2)
        path = res["path"]
        print(" ".join("D" if p == "dj" else "C" for p in path))

        if any(path[b] == "dj" for b in range(8, 12)):
            problems.append("showed the DJ angle while it was dark (bars 8-11)")
        if any(path[b] == "crowd" for b in range(0, 6)):
            problems.append("showed the crowd angle while it was out of focus (bars 0-5)")
        if path[14] != "crowd" or path[15] != "crowd":
            problems.append("crowd not shown for the drop bar and the one after")
        runs = [c["bars"] for c in res["cuts"]]
        if min(runs[:-1] or [2]) < 2:
            problems.append(f"a shot shorter than 2 bars: {runs}")
        # a shot may run past 4 bars only while the other angle is unusable (dark DJ 8-11, blurred crowd 0-5)
        usable = {"dj": set(range(N)) - set(range(8, 12)), "crowd": set(range(N)) - set(range(0, 6))}
        b0 = 0
        for c in res["cuts"]:
            span = set(range(b0, b0 + c["bars"]))
            other = "crowd" if c["angle"] == "dj" else "dj"
            if c["bars"] > 4 and len(span & usable[other]) >= 3:
                problems.append(f"{c['angle']} held {c['bars']} bars while {other} was usable for {len(span & usable[other])} of them")
            b0 += c["bars"]
        plan = sp.to_plan(res, angles)
        total = sum(c["duration"] for c in plan["cuts"])
        if abs(total - end) > 1e-6:
            problems.append(f"plan covers {total:.2f} s, expected {end:.2f}")
        crowd_cuts = [c for c in plan["cuts"] if c["source"] == "crowd"]
        first = next(c for c in res["cuts"] if c["angle"] == "crowd")
        if crowd_cuts and abs(crowd_cuts[0]["in"] - (first["start"] + CROWD_OFFSET)) > 1e-6:
            problems.append("crowd cut not mapped through the file offset")

    # strobe: a bright flash that comes back counts; a steady change does not
    flat = np.full((20, 18, 32), 0.3, np.float32)
    strobe = flat.copy()
    strobe[[4, 9, 14]] = 0.95
    step = flat.copy()
    step[10:] = 0.8
    if not (sp.bar_features(strobe)["strobe"] > 0.1 and sp.bar_features(step)["strobe"] == 0):
        problems.append("strobe detection")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
