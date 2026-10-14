"""The Creative Studio prototypes chained end to end, against a real filmcraft-cli build:
Serato history (a fake master.sqlite) -> track-ID captions; two synced camera angles +
the bar grid -> shot_picker -> plan; plan + captions -> plan_to_filmcraft -> a vertical
MP4. Checks the finished clip: 1080x1920, the right length, every cut on a bar line, an
ID caption burned in on both sides of the track change, and the set audio present.

Needs ffmpeg and FILMCRAFT_CLI (prints SKIP without them).

    python test_pipeline_e2e.py
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_to_filmcraft as p2f  # noqa: E402
import serato_set_grid as ssg  # noqa: E402
import shot_picker as sp  # noqa: E402
import test_plan_to_filmcraft as tp  # noqa: E402  (find_cli, frames)
import track_id_captions as tic  # noqa: E402

BAR, N = 1.6, 12  # 150 BPM, 12 bars = 19.2 s
REC_START = 1760100000  # recording started at this Unix time


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def main() -> int:
    cli = tp.find_cli()
    if not cli or not shutil.which("ffmpeg"):
        print("SKIP  needs ffmpeg and a filmcraft-cli build (set FILMCRAFT_CLI)")
        return 0
    problems = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # the set: clip window is recording seconds 600.0 .. 619.2; track B comes in at 609.6 (bar 6)
        clip0, end = 600.0, 600.0 + N * BAR
        db = d / "master.sqlite"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE history_session (id INTEGER PRIMARY KEY, start_time INTEGER, end_time INTEGER, file_name TEXT)")
        con.execute("CREATE TABLE history_entry (id INTEGER PRIMARY KEY, session_id INTEGER, file_name TEXT, artist TEXT, "
                    "name TEXT, bpm REAL, key TEXT, length_sec INTEGER, start_time INTEGER, played INTEGER, deck TEXT)")
        con.execute("INSERT INTO history_session VALUES (1, ?, -1, 's')", (REC_START,))
        for artist, title, at, played in [("A", "Opener", 300, 1), ("B", "Tool", 609.6, 1), ("C", "Skipped", 612, 0)]:
            con.execute("INSERT INTO history_entry (session_id, file_name, artist, name, bpm, key, length_sec, start_time, played, deck) "
                        "VALUES (1, ?, ?, ?, 150, 'Am', 400, ?, ?, '1')", (f"/m/{title}.mp3", artist, title, REC_START + at, played))
        con.commit()
        con.close()
        hist = ssg.relative_to_recording(ssg.read_history(db)["entries"], REC_START)
        tracks = [{"artist": h["artist"], "title": h["title"], "at_s": h["at_s_in_recording"], "played": h["played"]} for h in hist]
        segs = tic.segments(tracks, clip0, end)
        (d / "ids.srt").write_text(tic.to_srt(segs), encoding="utf-8")

        # two angles covering the clip window; files start at recording second 590 (dj) and 588 (crowd)
        span = N * BAR + 15
        # darkened so pure white can only come from the burned-in captions
        ff("-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={span}", "-vf", "eq=brightness=-0.25",
           "-pix_fmt", "yuv420p", str(d / "dj.mp4"))
        ff("-f", "lavfi", "-i", f"testsrc=size=1280x720:rate=30:duration={span}", "-vf", "hue=h=120,eq=brightness=-0.25",
           "-pix_fmt", "yuv420p", str(d / "crowd.mp4"))
        ff("-f", "lavfi", "-i", f"sine=frequency=110:duration={span}", "-ar", "48000", str(d / "set.wav"))
        angles = [sp.Angle("dj", str(d / "dj.mp4"), -590.0), sp.Angle("crowd", str(d / "crowd.mp4"), -588.0)]
        bars = [clip0 + i * BAR for i in range(N)]
        res = sp.pick(angles, bars, end, drop=clip0 + 8 * BAR, crowd="crowd", min_bars=2, max_bars=4)
        plan = sp.to_plan(res, angles, audio=str(d / "set.wav"), audio_offset=-590.0)
        plan.update({"name": "e2e", "captions": {"srt": str(d / "ids.srt"), "size": 48},
                     "export": {"path": str(d / "clip.mp4"), "crf": 22}})
        rep = p2f.build(plan, cli)

        out = d / "clip.mp4"
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                                          "-of", "json", str(out)], capture_output=True, text=True, check=True).stdout)["streams"]
        v = next(s for s in info if s["codec_type"] == "video")
        if (v["width"], v["height"]) != (1080, 1920):
            problems.append(f"size {v['width']}x{v['height']}")
        if not any(s["codec_type"] == "audio" for s in info):
            problems.append("no audio")
        f = tp.frames(out, 270, 480)
        if abs(len(f) - N * BAR * 30) > 1:
            problems.append(f"{len(f)} frames, expected {N * BAR * 30:.0f}")
        starts = [round(c["at"] * 30) for c in rep["cuts"]]
        if any(s % 48 for s in starts):  # 1.6 s bars at 30 fps = 48 frames
            problems.append(f"a cut is off the bar grid: {starts}")
        low = f[:, 300:470]
        white = ((low > 225).all(-1)).sum((1, 2))
        a_frame, b_frame = int(3.0 * 30), int(14.0 * 30)  # track A then track B on screen
        if not (white[a_frame] > 40 and white[b_frame] > 40):
            problems.append(f"ID captions missing: white px {white[a_frame]} / {white[b_frame]}")
        if [s["text"] for s in segs] != ["ID: A – Opener", "ID: B – Tool"]:
            problems.append(f"captions from history: {segs}")
        print(json.dumps({"path": "".join("D" if p == "dj" else "C" for p in res["path"]), "cut_frames": starts,
                          "captions": segs, "frames": len(f)}, ensure_ascii=False))
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
