"""Checks track_id_captions.py: captions follow the tracks inside the clip window, in clip
time; an unplayed load is skipped; a track audible for less than min_show is dropped; a
track without an artist still gets its title; the SRT is well formed.

    python test_track_id_captions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import track_id_captions as tic  # noqa: E402


def main() -> int:
    tracks = [
        {"artist": "Rødhåd", "title": "Target", "at_s": 1700.0},
        {"artist": "X", "title": "Loaded but never played", "at_s": 1830.0, "played": 0},
        {"artist": "Ancient Methods", "title": "Knights & Bishops", "at_s": 1845.0},
        {"artist": "", "title": "Untitled dub", "at_s": 1855.2},
        {"artist": "Y", "title": "Next", "at_s": 1900.0},
    ]
    segs = tic.segments(tracks, clip_start=1838.0, clip_end=1856.0, min_show=1.5)
    problems = []
    want = [{"start": 0.0, "end": 7.0, "text": "ID: Rødhåd – Target"},
            {"start": 7.0, "end": 17.2, "text": "ID: Ancient Methods – Knights & Bishops"}]
    if segs != want:
        problems.append(f"segments {segs}")
    segs2 = tic.segments(tracks, 1838.0, 1858.0, min_show=1.5)
    if segs2[-1]["text"] != "ID: Untitled dub":
        problems.append(f"title-only caption: {segs2[-1]}")
    srt = tic.to_srt(segs)
    if not srt.startswith("1\n00:00:00,000 --> 00:00:07,000\nID: Rødhåd – Target\n\n2\n00:00:07,000 --> 00:00:17,200\n"):
        problems.append(f"srt:\n{srt}")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
