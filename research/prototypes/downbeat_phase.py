"""Which beat is "one"? Pick the bar phase of a 4/4 techno grid from claps and changes.

Beat trackers and comb filters give you beats; in four-to-the-floor techno every beat has a
kick, so the kick says nothing about where the bar starts. Two cues usually do:
- the backbeat: claps/snares (1-5 kHz transients) on beats 2 and 4;
- changes: new parts, crashes and breakdown edges land on the first beat of a bar, most
  strongly at 8- and 16-bar phrase starts.
This scores the four possible phases on both cues and returns the downbeats, the phase, a
confidence (margin between the best and second-best phase) and phrase starts (8-bar
boundaries counted from the strongest change). Feed it beats from your comb-filter grid,
Beat This, or Serato's grid.

    python downbeat_phase.py track.wav --beats beats.txt

Limits: assumes 4/4 and a steady grid. Claps alone can't separate beat 1 from beat 3, so a
track with no structural changes in the analysed span comes back `half_bar_ambiguous` (check
it by ear or give it a longer span); tracks with no backbeat (some hardgroove, much
industrial) rely on the change cue alone.
"""
from __future__ import annotations

import argparse
import json
import sys

import librosa
import numpy as np


def beat_features(y: np.ndarray, sr: int, beats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per beat: clap strength (1-5 kHz onset energy just after the beat) and the mean log-mel
    spectrum over the beat (for bar-level novelty)."""
    hop = 256
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    band = (freqs >= 1000) & (freqs <= 5000)
    clap_env = librosa.onset.onset_strength(S=librosa.power_to_db(S[band]), sr=sr, hop_length=hop)
    mel = librosa.power_to_db(librosa.feature.melspectrogram(S=S, sr=sr, n_mels=48))
    frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
    w = max(1, int(0.06 * sr / hop))  # 60 ms after the beat
    clap = np.array([clap_env[f: f + w + 1].max() if 0 <= f < len(clap_env) else 0.0 for f in frames])
    edges = list(frames) + [frames[-1] + (frames[-1] - frames[-2] if len(frames) > 1 else 1)]
    beat_mel = np.stack([mel[:, max(0, edges[i]): max(edges[i] + 1, edges[i + 1])].mean(axis=1) for i in range(len(frames))])
    return clap, beat_mel


def bar_novelty(beat_mel: np.ndarray, phase: int) -> np.ndarray:
    """Distance between consecutive bars when bars start at beat index `phase` (mod 4)."""
    starts = np.arange(phase, len(beat_mel) - 3, 4)
    bars = np.stack([beat_mel[s: s + 4].mean(axis=0) for s in starts])
    return np.linalg.norm(np.diff(bars, axis=0), axis=1)


def choose_phase(clap: np.ndarray, beat_mel: np.ndarray, w_clap: float = 1.0, w_change: float = 4.0) -> dict:
    """Score phase p = index (mod 4) of beat 'one'.

    The backbeat (claps on 2 and 4) separates {1, 3} from {2, 4} but cannot tell beat 1 from
    beat 3: a bar shifted by two beats has its claps on 4 and 2. Only structure settles that
    half-bar question: sections change on bar lines, so with the right phase the biggest
    bar-to-bar jumps are sharp, and with a wrong one each change is split across two bars."""
    def z(v):
        sd = v.std()
        return (v - v.mean()) / sd if sd > 1e-9 else np.zeros_like(v)
    c = z(clap)
    idx = np.arange(len(c))
    backbeat, change = [], []
    for p in range(4):
        pos = (idx - p) % 4  # 0 = beat one
        backbeat.append(float(c[(pos == 1) | (pos == 3)].mean() - c[(pos == 0) | (pos == 2)].mean()))
        nov = bar_novelty(beat_mel, p)
        k = max(2, len(nov) // 8)
        change.append(float(np.sort(nov)[::-1][:k].mean()) if len(nov) else 0.0)
    ch = np.array(change)
    ref = float(np.median(ch)) or 1.0
    change_rel = (ch - ref) / ref
    scores = [w_clap * backbeat[p] + w_change * change_rel[p] for p in range(4)]
    order = np.argsort(scores)[::-1]
    best = int(order[0])
    other_half = (best + 2) % 4
    return {"phase": best, "scores": [round(float(x), 3) for x in scores],
            "confidence": round(float(scores[best] - scores[int(order[1])]), 3),
            "backbeat_clear": bool(max(backbeat) > 0.5),
            # claps narrowed it to beat 1 or beat 3, and structure didn't decide between them
            "half_bar_ambiguous": bool(abs(change_rel[best] - change_rel[other_half]) < 0.1),
            "change_rel": [round(float(x), 3) for x in change_rel]}


def phrases(beat_mel: np.ndarray, phase: int, bars_per_phrase: int = 8) -> list[int]:
    """Beat indices of phrase starts: 8-bar steps anchored at the bar with the biggest change."""
    nov = bar_novelty(beat_mel, phase)
    if len(nov) == 0:
        return []
    anchor = phase + 4 * (int(np.argmax(nov)) + 1)  # the bar that starts after the biggest jump
    step = 4 * bars_per_phrase  # a multiple of 4, so every phrase start is also a bar's beat one
    return list(range(anchor % step, len(beat_mel), step))


def analyse(y: np.ndarray, sr: int, beats: np.ndarray) -> dict:
    clap, beat_mel = beat_features(y, sr, beats)
    res = choose_phase(clap, beat_mel)
    res["downbeats"] = [round(float(t), 3) for t in beats[res["phase"]::4]]
    res["phrase_starts"] = [round(float(beats[i]), 3) for i in phrases(beat_mel, res["phase"])]
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("audio")
    ap.add_argument("--beats", required=True, help="text file, one beat time (s) per line")
    args = ap.parse_args(argv)
    y, sr = librosa.load(args.audio, sr=22050, mono=True)
    beats = np.array([float(x) for x in open(args.beats, encoding="utf-8") if x.strip()])
    print(json.dumps(analyse(y, sr, beats), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
