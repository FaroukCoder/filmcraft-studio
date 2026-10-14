"""Track-ID captions for a clip, from Serato's history (or better, from aligned track times).

The one thing club-clip audiences ask in the comments is "ID?". Serato already logged what
you played; this turns it into an SRT for the clip's time window: "ID: Artist – Title" for
each track while it is the one you hear, so `plan_to_filmcraft.py` can burn it in.

Track times, best first:
1. `serato_set_grid.py align` offsets: where each track actually sits in the recording;
2. Serato history `start_time` (via `serato_set_grid.py history --recording-start ...`), with
   `--lead` seconds added if your history marks the load rather than the moment it's heard
   (check one transition by ear; the report lists this as unverified).

    python track_id_captions.py tracks.json --clip-start 1838.0 --clip-end 1856.0 --out ids.srt

tracks.json: [{"artist": "...", "title": "...", "at_s": 1802.4, "played": 1}, ...] with times in
recording seconds (the `history` command's `at_s_in_recording` field works as `at_s`).
"""
from __future__ import annotations

import argparse
import json
import sys


def srt_time(t: float) -> str:
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments(tracks: list[dict], clip_start: float, clip_end: float, lead: float = 0.0,
             min_show: float = 1.5) -> list[dict]:
    """[{start, end, text}] in clip time for each track audible inside the window."""
    ts = sorted((t for t in tracks if t.get("played", 1) and t.get("at_s") is not None), key=lambda t: t["at_s"])
    out = []
    for i, t in enumerate(ts):
        a = float(t["at_s"]) + lead
        b = float(ts[i + 1]["at_s"]) + lead if i + 1 < len(ts) else float("inf")
        s, e = max(a, clip_start), min(b, clip_end)
        if e - s < min_show:
            continue
        artist = (t.get("artist") or "").strip()
        title = (t.get("title") or t.get("name") or "").strip()
        if not title:
            continue
        text = f"ID: {artist} – {title}" if artist else f"ID: {title}"
        out.append({"start": round(s - clip_start, 3), "end": round(e - clip_start, 3), "text": text})
    return out


def to_srt(segs: list[dict]) -> str:
    return "".join(f"{i}\n{srt_time(g['start'])} --> {srt_time(g['end'])}\n{g['text']}\n\n" for i, g in enumerate(segs, 1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tracks")
    ap.add_argument("--clip-start", type=float, required=True)
    ap.add_argument("--clip-end", type=float, required=True)
    ap.add_argument("--lead", type=float, default=0.0)
    ap.add_argument("--min-show", type=float, default=1.5)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    tracks = json.load(open(args.tracks, encoding="utf-8"))
    for t in tracks:
        if "at_s" not in t and "at_s_in_recording" in t:
            t["at_s"] = t["at_s_in_recording"]
    srt = to_srt(segments(tracks, args.clip_start, args.clip_end, args.lead, args.min_show))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(srt)
    else:
        sys.stdout.write(srt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
