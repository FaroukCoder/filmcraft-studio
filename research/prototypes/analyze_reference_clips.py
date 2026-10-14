"""Measure how reference club clips are cut (Top 10 #6).

For every video in a folder: find the cuts, track the beats, and report where the
cuts land relative to beats, bars and 8/16-bar phrases, how long shots last in
beats, how long the first shot holds, and where the biggest bass return ("drop")
sits. Writes two CSVs and prints the medians.

    python analyze_reference_clips.py CLIPS_DIR --out results/
    python analyze_reference_clips.py CLIPS_DIR --bpm-min 120 --bpm-max 160

Beat tracking uses Beat This (MIT) when it is installed (`pip install beat-this`,
needs PyTorch) and falls back to librosa otherwise. Cuts come from PySceneDetect
(BSD-3). Needs ffmpeg on PATH. Analysis only: never re-publish the clips.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


@dataclass
class ClipStats:
    clip: str
    duration_s: float
    bpm: float
    beat_source: str
    cuts: int
    cuts_per_10s: float
    median_shot_beats: float
    first_shot_beats: float
    cuts_on_beat_pct: float  # within 60 ms of a beat
    cuts_on_bar_pct: float  # on beat 1 of a bar
    cuts_on_phrase8_pct: float  # on a bar that starts an 8-bar phrase, counted from the drop
    drop_at_s: float | None
    drop_pct_of_clip: float | None


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def extract_audio(path: Path, wav: Path, sr: int = 22050) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), str(wav)],
        check=True,
    )


def _hsv_hist(frame) -> "np.ndarray":
    import cv2

    small = cv2.resize(frame, (96, 96))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1, 2], None, [12, 8, 4], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(h, h).flatten()


def persistent(path: Path, cuts: list[float], gap: float = 0.12, span: float = 0.3, min_dist: float = 0.3) -> list[float]:
    """Keep a candidate cut only if the picture *after* it differs from the picture
    *before* it. A strobe flash or a camera flash returns to the same picture, so the
    frames either side look alike; a real cut doesn't. Compares the median HSV
    histogram of [c-span, c-gap] with that of [c+gap, c+span]."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    def hist_over(t0: float, t1: float):
        hs = []
        for t in np.arange(max(t0, 0.0), t1, 1.0 / fps):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
            ok, frame = cap.read()
            if ok:
                hs.append(_hsv_hist(frame))
        return np.median(np.array(hs), axis=0).astype("float32") if hs else None

    kept = []
    for c in cuts:
        before, after = hist_over(c - span, c - gap), hist_over(c + gap, c + span)
        if before is None or after is None:
            kept.append(c)
            continue
        if cv2.compareHist(before, after, cv2.HISTCMP_BHATTACHARYYA) >= min_dist:
            kept.append(c)
    cap.release()
    return kept


def detect_cuts(path: Path, threshold: float, strobe_safe: bool = False, min_scene: str = "0.4s") -> list[float]:
    """Cut times. Club footage is full of strobes, which a content detector reads as
    cuts (a flash is a huge frame-to-frame change). strobe_safe keeps only cuts where
    the shot after differs from the shot before (see `persistent`)."""
    from scenedetect import ContentDetector, detect

    min_len = "0.1s" if strobe_safe else min_scene  # let flashes through, then judge them
    scenes = detect(str(path), ContentDetector(threshold=threshold, min_scene_len=min_len))
    # Each scene is (start, end); a cut is the start of every scene after the first.
    cuts = [s[0].get_seconds() for s in scenes[1:]]
    if strobe_safe:
        cuts = persistent(path, cuts)
        min_s = float(min_scene.rstrip("s")) if min_scene.endswith("s") else 0.4
        merged: list[float] = []
        for c in cuts:
            if not merged or c - merged[-1] >= min_s:
                merged.append(c)
        cuts = merged
    return cuts


def track_beats(wav: Path, bpm_min: float, bpm_max: float) -> tuple[np.ndarray, np.ndarray | None, str]:
    """Return (beat_times, downbeat_times or None, source)."""
    try:
        from beat_this.inference import File2Beats  # type: ignore

        f2b = File2Beats(checkpoint_path="small0", device="cpu", dbn=False)
        beats, downbeats = f2b(str(wav))
        return np.asarray(beats), np.asarray(downbeats), "beat_this"
    except Exception:
        pass
    import librosa

    y, sr = librosa.load(str(wav), sr=None, mono=True)
    # Kick-weighted onset envelope: low band only, which is where techno keeps time.
    onset = librosa.onset.onset_strength(y=y, sr=sr, fmax=200, n_mels=32)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, start_bpm=(bpm_min + bpm_max) / 2, units="frames")
    beats = librosa.frames_to_time(frames, sr=sr)
    return beats, None, "librosa"


def tempo_from_beats(beats: np.ndarray) -> float:
    """BPM from a least-squares fit of beat time against beat number. The median
    interval alone snaps to the tracker's frame grid (librosa at 22.05 kHz / 512 hop
    reads a 150 BPM track as 152): the same lag-grid trap whatstheID's analyser hit."""
    if len(beats) < 2:
        return 0.0
    diffs = np.diff(beats)
    period0 = float(np.median(diffs))
    # Number beats interval by interval (a gap of ~2 periods counts as a dropped beat).
    # Numbering from the first beat with the quantised period would drift by a whole
    # beat over a minute of music.
    steps = np.maximum(1, np.round(diffs / period0))
    idx = np.concatenate([[0.0], np.cumsum(steps)])
    slope, _ = np.polyfit(idx, beats, 1)
    return 60.0 / slope if slope > 0 else 0.0


def fold_tempo(bpm: float, lo: float, hi: float) -> float:
    while bpm < lo:
        bpm *= 2
    while bpm > hi:
        bpm /= 2
    return bpm


def bar_phase(beats: np.ndarray, downbeats: np.ndarray | None, wav: Path) -> int:
    """Index (0-3) of the beat that starts a bar. Uses tracker downbeats if present,
    otherwise picks the phase whose beats carry the most low-band onset energy."""
    if downbeats is not None and len(downbeats):
        first = int(np.argmin(np.abs(beats - downbeats[0])))
        return first % 4
    import librosa

    y, sr = librosa.load(str(wav), sr=None, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr, fmax=150, n_mels=24)
    idx = np.clip(librosa.time_to_frames(beats, sr=sr), 0, len(onset) - 1)
    energy = onset[idx]
    scores = [energy[p::4].mean() if len(energy[p::4]) else 0.0 for p in range(4)]
    return int(np.argmax(scores))


def find_drop(wav: Path, beats: np.ndarray) -> float | None:
    """Beat with the largest low-band (< 150 Hz) energy jump over the quietest of the
    previous 16 beats: a crude 'bass comes back' detector."""
    import librosa

    if len(beats) < 20:
        return None
    y, sr = librosa.load(str(wav), sr=None, mono=True)
    spec = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    low = spec[freqs < 150].sum(axis=0)
    frames = np.clip(librosa.time_to_frames(beats, sr=sr, hop_length=512), 0, len(low) - 1)
    per_beat = np.array([low[a:b].mean() if b > a else low[a] for a, b in zip(frames[:-1], frames[1:])])
    best, best_jump = None, 0.0
    for i in range(16, len(per_beat)):
        jump = per_beat[i] - per_beat[i - 16 : i].min()
        if jump > best_jump:
            best, best_jump = i, jump
    return float(beats[best]) if best is not None else None


def analyse(path: Path, args: argparse.Namespace, cut_rows: list[dict]) -> ClipStats:
    duration = probe_duration(path)
    cuts = detect_cuts(path, args.threshold, args.strobe_safe, args.min_scene)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        extract_audio(path, wav)
        beats, downbeats, source = track_beats(wav, args.bpm_min, args.bpm_max)
        phase = bar_phase(beats, downbeats, wav) if len(beats) else 0
        drop = find_drop(wav, beats) if len(beats) else None

    bpm = fold_tempo(tempo_from_beats(beats), args.bpm_min, args.bpm_max) if len(beats) > 1 else 0.0
    beat_period = 60.0 / bpm if bpm else 0.0
    # Phrase lines: the drop starts a phrase in club tracks, so count 8-bar steps from
    # the bar the drop lands in (or from the first downbeat when no drop is found).
    anchor_bar = 0
    if drop is not None and len(beats):
        anchor_bar = (int(np.argmin(np.abs(beats - drop))) - phase) // 4
    on_beat = on_bar = on_phrase = 0
    for c in cuts:
        if not len(beats):
            break
        i = int(np.argmin(np.abs(beats - c)))
        off_ms = (c - beats[i]) * 1000.0
        idx_in_bar = (i - phase) % 4
        bar_index = (i - phase) // 4
        is_beat = abs(off_ms) <= args.tolerance_ms
        is_bar = is_beat and idx_in_bar == 0
        is_phrase = is_bar and (bar_index - anchor_bar) % 8 == 0
        on_beat += is_beat
        on_bar += is_bar
        on_phrase += is_phrase
        cut_rows.append({
            "clip": path.name, "cut_s": round(c, 3), "nearest_beat_s": round(float(beats[i]), 3),
            "offset_ms": round(off_ms, 1), "beat_in_bar": idx_in_bar + 1,
            "bar_in_phrase8": (bar_index - anchor_bar) % 8 + 1,
        })
    edges = [0.0, *cuts, duration]
    shots = [b - a for a, b in zip(edges[:-1], edges[1:]) if b > a]
    shot_beats = [s / beat_period for s in shots] if beat_period else []
    n = max(len(cuts), 1)
    return ClipStats(
        clip=path.name, duration_s=round(duration, 2), bpm=round(bpm, 2), beat_source=source,
        cuts=len(cuts), cuts_per_10s=round(10 * len(cuts) / duration, 2) if duration else 0.0,
        median_shot_beats=round(statistics.median(shot_beats), 1) if shot_beats else 0.0,
        first_shot_beats=round(shot_beats[0], 1) if shot_beats else 0.0,
        cuts_on_beat_pct=round(100 * on_beat / n, 1) if cuts else 0.0,
        cuts_on_bar_pct=round(100 * on_bar / n, 1) if cuts else 0.0,
        cuts_on_phrase8_pct=round(100 * on_phrase / n, 1) if cuts else 0.0,
        drop_at_s=round(drop, 2) if drop is not None else None,
        drop_pct_of_clip=round(100 * drop / duration, 1) if drop is not None and duration else None,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clips", type=Path)
    ap.add_argument("--out", type=Path, default=Path("reference_stats"))
    ap.add_argument("--bpm-min", type=float, default=118.0)
    ap.add_argument("--bpm-max", type=float, default=160.0)
    ap.add_argument("--threshold", type=float, default=27.0, help="PySceneDetect ContentDetector threshold")
    ap.add_argument("--tolerance-ms", type=float, default=60.0, help="how close to a beat counts as 'on' it")
    ap.add_argument("--strobe-safe", action="store_true", help="reject flashes: keep cuts whose before/after shots differ")
    ap.add_argument("--min-scene", default="0.4s", help="shortest shot to accept, e.g. 0.4s")
    args = ap.parse_args(argv)

    files = sorted(p for p in args.clips.iterdir() if p.suffix.lower() in VIDEO_EXT)
    if not files:
        print(f"no videos in {args.clips}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    stats: list[ClipStats] = []
    cut_rows: list[dict] = []
    for f in files:
        try:
            stats.append(analyse(f, args, cut_rows))
            print(f"ok   {f.name}")
        except Exception as e:  # one bad file must not stop the batch
            print(f"skip {f.name}: {e}", file=sys.stderr)
    if not stats:
        return 1
    with open(args.out / "clips.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(asdict(stats[0])))
        w.writeheader()
        w.writerows(asdict(s) for s in stats)
    if cut_rows:
        with open(args.out / "cuts.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cut_rows[0]))
            w.writeheader()
            w.writerows(cut_rows)
    print("\nmedians over", len(stats), "clips")
    for key in ("duration_s", "cuts", "cuts_per_10s", "median_shot_beats", "first_shot_beats",
                "cuts_on_beat_pct", "cuts_on_bar_pct", "cuts_on_phrase8_pct", "drop_pct_of_clip"):
        vals = [getattr(s, key) for s in stats if getattr(s, key) is not None]
        if vals:
            print(f"  {key:22s} {statistics.median(vals)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
