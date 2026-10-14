"""Checks downbeat_phase.py on synthetic 150 BPM techno: kick on every beat, claps on 2 and 4,
off-beat hats, an 8-bar breakdown (bars 16-23, no kick), the drop on bar 24 with crashes on
bars 24, 32 and 40. The beat list starts on beat 3 of a bar, so the right phase is 2. Three
versions: claps + structure, structure only (no claps, as in much hardgroove), claps only
(no breakdown or crashes), which can only narrow it to beats 1/3 and must report that ambiguity.
Phrase starts are counted in 8-bar steps from the first bar (bar 0, even though the beat list
starts mid-bar), and bar novelty (breakdown at 16, drop at 24) must agree with them.

    python test_downbeat_phase.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import downbeat_phase as dp  # noqa: E402

SR, BPM, BARS = 22050, 150.0, 48
BEAT = 60 / BPM


def synth(claps: bool, structure: bool, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n_beats = BARS * 4
    y = np.zeros(int((n_beats + 4) * BEAT * SR))
    def put(t, sig):
        i = int(t * SR)
        y[i:i + len(sig)] += sig[: max(0, len(y) - i)]
    tk = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 120 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 9)
    tc = np.arange(int(0.12 * SR)) / SR
    clap_sig = np.convolve(rng.normal(0, 1, len(tc)), np.ones(3) / 3, "same") * np.exp(-tc * 35) * 0.5
    clap_sig = clap_sig - np.convolve(clap_sig, np.ones(25) / 25, "same")  # crude high-pass toward 1-5 kHz
    th = np.arange(int(0.05 * SR)) / SR
    hat = np.diff(rng.normal(0, 1, len(th) + 1)) * np.exp(-th * 80) * 0.15
    crash = np.diff(rng.normal(0, 1, int(1.5 * SR) + 1)) * np.exp(-np.arange(int(1.5 * SR)) / SR * 2.5) * 0.4
    tp = np.arange(int(4 * BEAT * SR)) / SR
    pad = 0.12 * np.sin(2 * np.pi * 220 * tp) * np.sin(np.pi * tp / tp[-1])
    for b in range(n_beats):
        bar, pos = divmod(b, 4)
        t = 0.1 + b * BEAT
        breakdown = structure and 16 <= bar < 24
        if not breakdown:
            put(t, kick)
            put(t + BEAT / 2, hat)
            if claps and pos in (1, 3):
                put(t + 0.005, clap_sig)
        elif pos == 0:
            put(t, pad)
        if structure and pos == 0 and bar in (24, 32, 40):
            put(t, crash)
    y += rng.normal(0, 0.003, len(y))
    beats = 0.1 + np.arange(2, n_beats) * BEAT  # the list starts on beat 3 of bar 0
    return y.astype(np.float32), beats


def main() -> int:
    problems = []
    for claps, structure in [(True, True), (False, True), (True, False)]:
        y, beats = synth(claps, structure)
        res = dp.analyse(y, SR, beats)
        tag = f"claps={claps} structure={structure}"
        print(tag, "phase", res["phase"], "confidence", res["confidence"], "scores", res["scores"])
        if structure and res["phase"] != 2:
            problems.append(f"{tag}: phase {res['phase']}, want 2")
        if not structure and not (res["phase"] in (0, 2) and res["half_bar_ambiguous"]):
            problems.append(f"{tag}: claps alone can only narrow it to beat 1 or 3; must say so: {res}")
        if structure:
            starts = {round((t - 0.1) / (4 * BEAT)) for t in res["phrase_starts"]}
            if not {0, 8, 16, 24, 32, 40} <= starts:
                problems.append(f"{tag}: phrase starts at bars {sorted(starts)}, want every 8th bar from 0")
            if res["phrase_novelty_offset_bars"] != 0 or res["phrase_novelty_disagrees"]:
                problems.append(f"{tag}: the breakdown and drop sit on phrase lines, novelty should agree: {res}")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
