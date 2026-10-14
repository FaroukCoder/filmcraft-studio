"""Synthetic check for analyze_reference_clips.py.

Builds a 24 s clip at 150 BPM (kick on every beat, accented on beat 1, a two-bar
breakdown with no kick, then the kick returns at 16.0 s) with seven cuts at known
times, runs the analyser and checks what it reports.

    python test_analyze_reference_clips.py
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_reference_clips as arc  # noqa: E402

SR = 22050
BPM = 150.0
BEAT = 60.0 / BPM  # 0.4 s
DURATION = 24.0
BREAKDOWN = (12.8, 16.0)  # bars 9-10: no kick
CUTS = [3.2, 6.4, 8.0, 12.83, 14.5, 16.0, 20.0]
# expected: on beat (<=60 ms): all but 14.5 -> 6/7; on bar: 3.2 6.4 8.0 12.83 16.0 -> 5/7;
# phrase lines are counted from the drop (bar 10), so bars 2, 10, 18: 3.2 and 16.0 -> 2/7


def kick(amp: float) -> np.ndarray:
    t = np.arange(int(0.18 * SR)) / SR
    freq = 50 + 90 * np.exp(-t * 30)  # pitch drop, like a kick
    return amp * np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 18)


def write_audio(path: Path) -> None:
    y = np.zeros(int(DURATION * SR))
    n_beats = int(DURATION / BEAT)
    for i in range(n_beats):
        t = i * BEAT
        if BREAKDOWN[0] <= t < BREAKDOWN[1]:
            continue
        k = kick(0.9 if i % 4 == 0 else 0.6)
        s = int(t * SR)
        y[s : s + len(k)] += k[: len(y) - s]
    rng = np.random.default_rng(0)
    y += 0.01 * rng.standard_normal(len(y))  # a little hiss, like a room mic
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_video(audio: Path, out: Path) -> None:
    # alternate luma hard so every cut is visible to a content detector
    colours = ["black", "white", "red", "black", "white", "blue", "black", "yellow"]
    edges = [0.0, *CUTS, DURATION]
    inputs, labels = [], []
    for i, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        inputs += ["-f", "lavfi", "-i", f"color=c={colours[i % len(colours)]}:s=320x568:r=25:d={b - a:.3f}"]
        labels.append(f"[{i}:v]")
    n = len(labels)
    filt = "".join(labels) + f"concat=n={n}:v=1:a=0[v]"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(audio), "-filter_complex", filt,
         "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)],
        check=True,
    )


def add_strobes(src: Path, dst: Path, start: float, end: float, every: float = 0.4) -> None:
    """White flash for 2 frames every `every` seconds between start and end (no real cut)."""
    on = "+".join(f"between(t,{t:.2f},{t + 0.08:.2f})" for t in np.arange(start, end, every))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf",
                    f"eq=brightness=0.9:enable='{on}'", "-c:a", "copy", str(dst)], check=True)


def strobe_check(tmp: Path) -> list[str]:
    """Strobes inside one shot (8.0-12.8 s) must not become cuts in strobe-safe mode."""
    clean = tmp / "clips" / "synthetic.mp4"
    strobe_dir = tmp / "strobe"
    strobe_dir.mkdir()
    add_strobes(clean, strobe_dir / "strobe.mp4", 8.6, 12.4)
    plain = arc.detect_cuts(strobe_dir / "strobe.mp4", 27.0, strobe_safe=False)
    safe = arc.detect_cuts(strobe_dir / "strobe.mp4", 27.0, strobe_safe=True)
    print(f"strobes: plain detector {len(plain)} cuts, strobe-safe {len(safe)} cuts (true 7)")
    problems = []
    if abs(len(safe) - len(CUTS)) > 1:
        problems.append(f"strobe-safe found {len(safe)} cuts {safe}")
    if len(plain) <= len(safe):
        problems.append("expected the plain detector to be fooled by strobes more than strobe-safe")
    return problems


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clips = tmp / "clips"
        clips.mkdir()
        write_audio(tmp / "a.wav")
        write_video(tmp / "a.wav", clips / "synthetic.mp4")
        out = tmp / "out"
        rc = arc.main([str(clips), "--out", str(out)])
        assert rc == 0, rc
        row = next(csv.DictReader(open(out / "clips.csv", encoding="utf-8")))
        cuts = list(csv.DictReader(open(out / "cuts.csv", encoding="utf-8")))
        strobe_problems = strobe_check(tmp)
    print(row)
    found = [float(c["cut_s"]) for c in cuts]
    problems = []
    if len(found) != len(CUTS):
        problems.append(f"cuts: expected {len(CUTS)}, found {len(found)} {found}")
    elif max(abs(a - b) for a, b in zip(found, CUTS)) > 0.05:
        problems.append(f"cut times off: {found}")
    if abs(float(row["bpm"]) - BPM) > 0.3:
        problems.append(f"bpm {row['bpm']}")
    if abs(float(row["cuts_on_beat_pct"]) - 85.7) > 0.1:
        problems.append(f"on-beat {row['cuts_on_beat_pct']} (want 85.7)")
    if abs(float(row["cuts_on_bar_pct"]) - 71.4) > 0.1:
        problems.append(f"on-bar {row['cuts_on_bar_pct']} (want 71.4)")
    if abs(float(row["cuts_on_phrase8_pct"]) - 28.6) > 0.1:
        problems.append(f"on-phrase {row['cuts_on_phrase8_pct']} (want 28.6)")
    if not row["drop_at_s"] or abs(float(row["drop_at_s"]) - 16.0) > 0.45:
        problems.append(f"drop at {row['drop_at_s']} (want 16.0)")
        # beats must sit on the kicks, not on the onset envelope's late peak (19-31 ms on a
        # recorded loop), or a cut one frame before the kick reads as off-beat
        beats, _, _ = arc.track_beats(tmp / "a.wav", 118, 175)
        true = np.arange(0, DURATION, BEAT)
        err = np.array([np.min(np.abs(true - b)) for b in beats if not (BREAKDOWN[0] <= b < BREAKDOWN[1])])
        if len(err) == 0 or float(np.median(err)) > 0.010:
            problems.append(f"beats are {1000 * float(np.median(err)) if len(err) else -1:.1f} ms off the kicks")
    problems += strobe_problems
    if problems:
        print("FAIL\n  " + "\n  ".join(problems))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
