"""Beat grid for your own DJ set from Serato's history and your own track files (Top 10 #7).

Step 1, `history`: read Serato DJ 4's `master.sqlite` (read-only) and list what you
played in a session: artist, title, BPM, key, deck, start time, and where each load
sits relative to the start of your set recording.

Step 2, `align`: find where a track you own sits inside the recording and how much
it was sped up or slowed down, by cross-correlating onset envelopes (150 Hz-8 kHz) over a
ladder of stretch ratios (the same idea as whatstheID's query-side speed ladder).
With the track's own grid (BPM + first downbeat, e.g. from its Serato BeatGrid tag)
that gives every beat of that track in set time:  t_set = offset + t_track / ratio.

    python serato_set_grid.py history --db "%LOCALAPPDATA%/Serato/Library/master.sqlite" \
        --recording-start "2026-10-10 23:41:05"
    python serato_set_grid.py align --mix set.wav --track track.mp3 --near 1830 \
        --bpm 148.0 --first-downbeat 0.112

Schema as read by the open-source whats-now-playing project (history_session,
history_entry). Serato 3.x keeps history in `_Serato_/History/Sessions/*.session`
instead; that format is not handled here. Times are assumed to be Unix seconds,
as in that project's tests: check one row against your own recording.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- history

def read_history(db: Path, session_id: int | None = None) -> dict:
    """Entries of one session (the newest by default), oldest first."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        if session_id is None:
            row = con.execute("SELECT id FROM history_session ORDER BY start_time DESC LIMIT 1").fetchone()
            if row is None:
                return {"session": None, "entries": []}
            session_id = row["id"]
        sess = dict(con.execute("SELECT id, start_time, end_time FROM history_session WHERE id = ?",
                                (session_id,)).fetchone())
        rows = con.execute(
            "SELECT artist, name AS title, bpm, key, deck, start_time, played, file_name, length_sec "
            "FROM history_entry WHERE session_id = ? ORDER BY start_time", (session_id,)).fetchall()
        return {"session": sess, "entries": [dict(r) for r in rows]}
    finally:
        con.close()


def relative_to_recording(entries: list[dict], recording_start_unix: float) -> list[dict]:
    out = []
    for e in entries:
        e = dict(e)
        e["at_s_in_recording"] = None if e["start_time"] is None else float(e["start_time"]) - recording_start_unix
        out.append(e)
    return out


# --------------------------------------------------------------------------- alignment

def onset_envelope(path: Path, sr: int = 22050, hop: int = 256) -> tuple[np.ndarray, float]:
    """Onset envelope over 150 Hz-8 kHz, and frames/second.

    Not the kick band: a four-on-the-floor kick is periodic, so it can't tell one bar
    from the next, and DJs cut the incoming track's bass during a blend anyway. Hats,
    percussion and synth stabs vary from bar to bar and survive the EQ."""
    import librosa

    y, _ = librosa.load(str(path), sr=sr, mono=True)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, fmin=150, fmax=8000, n_mels=40)
    env = (env - env.mean()) / (env.std() + 1e-9)
    return env.astype(np.float32), sr / hop


def _stretch(env: np.ndarray, ratio: float) -> np.ndarray:
    """The track as it sounds played at `ratio` x speed: `ratio` > 1 means shorter."""
    n = max(2, int(round(len(env) / ratio)))
    return np.interp(np.linspace(0, len(env) - 1, n), np.arange(len(env)), env).astype(np.float32)


def align(mix_env: np.ndarray, trk_env: np.ndarray, fps: float, near_s: float | None = None,
          search_s: float = 240.0, max_shift: float = 0.08, step: float = 0.0025,
          excerpt_s: float = 60.0) -> dict:
    """Best (offset_s, ratio, score) for a track inside a mix.

    Uses an excerpt from the middle of the track (intros and outros are where the
    other deck plays too) and searches offsets within +/- search_s of `near_s`."""
    from scipy.signal import fftconvolve

    mid = len(trk_env) // 2
    half = int(excerpt_s * fps / 2)
    exc = trk_env[max(0, mid - half): mid + half]
    exc_start_s = max(0, mid - half) / fps
    if near_s is None:
        lo, hi = 0, len(mix_env)
    else:
        lo = max(0, int((near_s - search_s) * fps))
        hi = min(len(mix_env), int((near_s + search_s + excerpt_s) * fps) + len(exc))
    window = mix_env[lo:hi]
    best = {"score": -np.inf}
    for ratio in np.arange(1 - max_shift, 1 + max_shift + 1e-9, step):
        e = _stretch(exc, ratio)
        if len(e) >= len(window):
            continue
        corr = fftconvolve(window, e[::-1], mode="valid") / len(e)
        k = int(np.argmax(corr))
        if corr[k] > best["score"]:
            # where the excerpt starts in the mix, minus how far into the track it starts
            start_mix_s = (lo + k) / fps
            best = {"score": float(corr[k]), "ratio": float(ratio),
                    "offset_s": start_mix_s - exc_start_s / ratio}
    if np.isfinite(best["score"]):
        # sharpness: best vs typical correlation tells a real match from noise
        best["score"] = round(float(best["score"]), 4)
        best["ratio"] = round(float(best["ratio"]), 4)
        best["offset_s"] = round(float(best["offset_s"]), 3)
    return best


def beats_in_set(offset_s: float, ratio: float, bpm: float, first_downbeat_s: float,
                 track_len_s: float) -> list[tuple[float, int]]:
    """(time in set, beat number in bar 1-4) for every beat of the track's own grid."""
    period = 60.0 / bpm
    out, i = [], 0
    t = first_downbeat_s
    while t < track_len_s:
        out.append((round(offset_s + t / ratio, 4), i % 4 + 1))
        i += 1
        t = first_downbeat_s + i * period
    return out


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("history")
    h.add_argument("--db", type=Path, required=True)
    h.add_argument("--session", type=int)
    h.add_argument("--recording-start", help="local time the recording started, 'YYYY-MM-DD HH:MM:SS'")
    a = sub.add_parser("align")
    a.add_argument("--mix", type=Path, required=True)
    a.add_argument("--track", type=Path, required=True)
    a.add_argument("--near", type=float, help="expected position in the mix (s), e.g. from `history`")
    a.add_argument("--bpm", type=float)
    a.add_argument("--first-downbeat", type=float, default=0.0)
    args = ap.parse_args(argv)

    if args.cmd == "history":
        hist = read_history(args.db, args.session)
        entries = hist["entries"]
        if args.recording_start:
            start = dt.datetime.strptime(args.recording_start, "%Y-%m-%d %H:%M:%S").timestamp()
            entries = relative_to_recording(entries, start)
        print(json.dumps({"session": hist["session"], "entries": entries}, indent=2, ensure_ascii=False))
        return 0

    mix_env, fps = onset_envelope(args.mix)
    trk_env, _ = onset_envelope(args.track)
    res = align(mix_env, trk_env, fps, near_s=args.near)
    if args.bpm:
        res["beats"] = beats_in_set(res["offset_s"], res["ratio"], args.bpm, args.first_downbeat, len(trk_env) / fps)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
