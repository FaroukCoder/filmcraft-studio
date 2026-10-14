"""Checks serato_set_grid.py: history reading on a fake master.sqlite, and alignment
of a track inside a synthetic DJ mix where it plays 3 % fast, with its bass cut during
the blend and crowd noise on top.

    python test_serato_set_grid.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import serato_set_grid as ssg  # noqa: E402

SR = 22050


def _tone(freq, dur, decay, amp):
    t = np.arange(int(dur * SR)) / SR
    return amp * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)


def _noise(dur, decay, amp, rng):
    t = np.arange(int(dur * SR)) / SR
    return amp * rng.standard_normal(len(t)) * np.exp(-t * decay)


def make_track(bpm: float, seconds: float, seed: int) -> np.ndarray:
    """Kick on every beat, plus hats, claps and stabs whose pattern changes every bar
    (so bars are distinguishable), and an 8-bar breakdown without kick."""
    rng = np.random.default_rng(seed)
    y = np.zeros(int(seconds * SR))
    beat = 60 / bpm
    n_beats = int(seconds / beat)
    kick = _tone(55, 0.2, 18, 0.8)
    for i in range(n_beats):
        bar = i // 4
        t0 = int(i * beat * SR)
        if not (32 <= bar < 40):  # breakdown
            y[t0:t0 + len(kick)] += kick[: len(y) - t0]
        for sub in range(4):  # 16th-note grid, random per bar but fixed per seed
            if rng.random() < 0.45:
                s = int((i * beat + sub * beat / 4) * SR)
                h = _noise(0.04, 80, 0.25, rng)
                y[s:s + len(h)] += h[: len(y) - s]
        if rng.random() < 0.3:
            s = int((i * beat + beat / 2) * SR)
            st = _tone(rng.choice([440, 523, 659, 784]), 0.15, 12, 0.3)
            y[s:s + len(st)] += st[: len(y) - s]
    return y


def resample_speed(y: np.ndarray, ratio: float) -> np.ndarray:
    """Play y at `ratio` x speed (pitch moves too, like a DJ without key lock)."""
    n = int(len(y) / ratio)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def highpass(y: np.ndarray, cutoff: float = 250.0) -> np.ndarray:
    from scipy.signal import butter, sosfilt

    return sosfilt(butter(4, cutoff, "hp", fs=SR, output="sos"), y)


def write_wav(path: Path, y: np.ndarray) -> None:
    pcm = (np.clip(y / (np.abs(y).max() + 1e-9) * 0.9, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # ---- history
        db = tmp / "master.sqlite"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE history_session (id INTEGER PRIMARY KEY, start_time INTEGER, end_time INTEGER, file_name TEXT)")
        con.execute("CREATE TABLE history_entry (id INTEGER PRIMARY KEY, session_id INTEGER, file_name TEXT, artist TEXT, "
                    "name TEXT, bpm REAL, key TEXT, length_sec INTEGER, start_time INTEGER, played INTEGER, deck TEXT)")
        con.execute("INSERT INTO history_session VALUES (1, 1760000000, 1760007200, 's1')")
        con.execute("INSERT INTO history_session VALUES (2, 1760100000, -1, 's2')")
        for i, (artist, title, start) in enumerate([("A", "One", 1760100060), ("B", "Two", 1760100400), ("C", "Three", 1760100700)]):
            con.execute("INSERT INTO history_entry (session_id, file_name, artist, name, bpm, key, length_sec, start_time, played, deck) "
                        "VALUES (2, ?, ?, ?, 148.0, 'Am', 400, ?, 1, ?)", (f"/m/{title}.mp3", artist, title, start, str(i % 2 + 1)))
        con.commit()
        con.close()
        hist = ssg.read_history(db)
        rel = ssg.relative_to_recording(hist["entries"], 1760100000)
        if [e["title"] for e in rel] != ["One", "Two", "Three"] or rel[1]["at_s_in_recording"] != 400:
            problems.append(f"history: {rel}")

        # ---- alignment
        track_a = make_track(140, 150, seed=1)
        track_b = make_track(140, 120, seed=2)
        ratio, offset = 1.03, 50.0
        a_fast = resample_speed(track_a, ratio)
        mix = np.zeros(int((offset + len(a_fast) / SR + 5) * SR))
        mix[: len(track_b)] += track_b
        s = int(offset * SR)
        blend_end = int((offset + 30) * SR)  # 30 s blend with A's bass cut
        a_mix = a_fast.copy()
        a_mix[: blend_end - s] = highpass(a_fast[: blend_end - s])
        mix[s:s + len(a_mix)] += a_mix[: len(mix) - s]
        mix += 0.05 * np.random.default_rng(9).standard_normal(len(mix))  # crowd
        write_wav(tmp / "mix.wav", mix)
        write_wav(tmp / "a.wav", track_a)
        mix_env, fps = ssg.onset_envelope(tmp / "mix.wav")
        trk_env, _ = ssg.onset_envelope(tmp / "a.wav")
        res = ssg.align(mix_env, trk_env, fps, near_s=60.0)
        print("alignment:", res)
        if abs(res["ratio"] - ratio) > 0.003:
            problems.append(f"ratio {res['ratio']} (want {ratio})")
        if abs(res["offset_s"] - offset) > 0.05:
            problems.append(f"offset {res['offset_s']} (want {offset})")
        beats = ssg.beats_in_set(res["offset_s"], res["ratio"], 140.0, 0.0, 150.0)
        # beat 100 of the track (t = 100 * 60/140 s) should land at offset + t / ratio in the set
        want = offset + 100 * 60 / 140 / ratio
        if abs(beats[100][0] - want) > 0.06:
            problems.append(f"beat 100 at {beats[100][0]} (want {want:.3f})")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
