"""DJ-set analysis (master plan P2, Q11/Q16): sync the camera to the clean Serato recording, then
find the moments worth posting. Drops first (the bass returning after a breakdown); mix
transitions, crowd/hands-on moments (vision) and track IDs (whatstheID) come later.

Everything is numpy over a mono 11025 Hz signal, so a 2 h set fits in memory (~80 MB)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

SR = 11025
WIN = 0.25  # seconds per energy window


def load_audio(path: Path, sr: int = SR, seconds: float | None = None) -> np.ndarray:
    args = ["ffmpeg", "-v", "error", "-i", str(path)] + (["-t", str(seconds)] if seconds else []) \
        + ["-f", "s16le", "-ac", "1", "-ar", str(sr), "-"]
    pcm = subprocess.run(args, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


def _envelope(y: np.ndarray, sr: int, rate: int = 200) -> np.ndarray:
    """Onset envelope at `rate` Hz: rectified, block-averaged, positive differences. It ignores
    level and EQ differences between a phone mic and the clean recording."""
    hop = sr // rate
    n = len(y) // hop
    env = np.abs(y[: n * hop]).reshape(n, hop).mean(axis=1)
    env = np.log1p(env * 100)
    d = np.maximum(np.diff(env, prepend=env[:1]), 0)
    return (d - d.mean()) / (d.std() + 1e-9)


def _xcorr(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cross-correlation of a against b for every lag (a[t + lag] ~ b[t])."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    xc = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    lags = np.r_[np.arange(0, len(a)), np.arange(-len(b) + 1, 0)]
    return np.r_[xc[: len(a)], xc[n - len(b) + 1:]], lags


def sync_offset(clean: np.ndarray, camera: np.ndarray, sr: int = SR, max_lag: float = 600.0,
                rate: int = 200) -> tuple[float, float]:
    """Seconds into the clean recording at which the camera's recording starts, and a
    confidence. Coarse: onset envelopes at `rate` Hz find the right place. Fine: the raw
    waveforms around it (+-0.3 s) give sample precision. Techno repeats every beat, so the
    confidence is how far the coarse peak stands above the typical correlation (z-score,
    > 8 is solid), not peak vs runner-up (the runner-up is the same groove one bar away)."""
    xc, lags = _xcorr(_envelope(clean, sr, rate), _envelope(camera, sr, rate))
    ok = (lags >= 0) & (lags <= max_lag * rate)
    xc, lags = xc[ok], lags[ok]
    best = int(np.argmax(xc))
    z = (xc[best] - np.median(xc)) / (xc.std() + 1e-9)
    coarse = lags[best] / rate
    # fine: 20 s of camera from its middle, against the clean signal around the coarse guess
    seg0 = max(0, len(camera) // 2 - 10 * sr)
    cam = camera[seg0: seg0 + 20 * sr]
    c0 = int((coarse + seg0 / sr - 0.3) * sr)
    if c0 < 0 or c0 + len(cam) + int(0.6 * sr) > len(clean):
        return round(coarse, 3), round(float(z), 1)
    ref = clean[c0: c0 + len(cam) + int(0.6 * sr)]
    fx, flags = _xcorr(ref - ref.mean(), cam - cam.mean())
    good = (flags >= 0) & (flags <= int(0.6 * sr))
    lag = flags[good][int(np.argmax(fx[good]))]
    return round((c0 + lag) / sr - seg0 / sr, 4), round(float(z), 1)


def low_energy(y: np.ndarray, sr: int = SR, win: float = WIN) -> np.ndarray:
    """Kick + bass energy (30-300 Hz) per `win`-second window."""
    n = int(win * sr)
    frames = y[: len(y) // n * n].reshape(-1, n)
    spec = np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / sr)
    return spec[:, (f >= 30) & (f < 300)].sum(axis=1)


def find_drops(y: np.ndarray, sr: int = SR, before: float = 8.0, after: float = 3.0,
               max_before: float = 0.25, min_after: float = 0.4) -> list[dict]:
    """Drops: the bass/kick returning after a breakdown. At every window compare the mean
    low-band level (relative to the local 60 s level) over the `before` s leading up to it with
    the `after` s following it: a drop is a peak of that contrast where the run-up was a real
    breakdown (< `max_before`) and the bass came back (> `min_after`). Means, not every-frame
    thresholds, so a sub-bass riser in the break or a dip after the drop doesn't hide it.
    The time is then pinned to the strongest kick onset within 1 s. Score = breakdown depth
    and length (tension) x how hard it comes back."""
    raw = low_energy(y, sr)
    k = int(1 / WIN)
    e = np.convolve(raw, np.ones(k) / k, mode="same")  # 1 s smoothing
    w = int(60 / WIN)  # local level: 75th percentile over a 60 s window
    pad = np.pad(e, w // 2, mode="edge")
    level = np.array([np.percentile(pad[i:i + w], 75) for i in range(len(e))]) + 1e-12
    r = e / level
    nb, na = int(before / WIN), int(after / WIN)
    cs = np.r_[0, np.cumsum(r)]
    cand = []
    for i in range(nb, len(r) - na):
        pre = (cs[i - 1] - cs[i - nb]) / (nb - 1)  # leave out the frame the smoothing leaks into
        post = (cs[i + na + 1] - cs[i + 2]) / (na - 1)
        if pre < max_before and post > min_after:
            cand.append((post - pre, i, pre, post))
    drops: list[dict] = []
    for contrast, i, pre, post in sorted(cand, reverse=True):  # non-max suppression: 10 s apart
        if any(abs(i * WIN - d["time"]) < 10 for d in drops):
            continue
        # the contrast peaks once the window is past the drop, so search back up to 3 s for the
        # first window where the bass reaches half its post-drop level: the first kick back
        post_raw = raw[i + 2:i + na + 1].mean()
        j = next((x for x in range(max(0, i - 3 * k), i + 1) if raw[x] > 0.5 * post_raw), i)
        brk = 0  # breakdown length: how far back from the drop onset the bass stays low
        while j - brk - 2 >= 0 and r[j - brk - 2] < max_before * 1.5 and brk * WIN < 60:
            brk += 1  # (from j - 2: the 1 s smoothing leaks the first kicks back a window)
        drops.append({"time": round(j * WIN, 2), "break": round(brk * WIN, 1),
                      "score": round(min(brk * WIN, 30) * float(np.log1p(post / (pre + 0.02))), 2)})
    return sorted(drops, key=lambda d: -d["score"])


def local_bpm(y: np.ndarray, at: float, sr: int = SR, span: float = 12.0) -> float | None:
    """Tempo right after `at` from the autocorrelation of the low-band onset (118-150 BPM)."""
    seg = y[int(at * sr): int((at + span) * sr)]
    if len(seg) < sr * 4:
        return None
    rate = 200
    env = _envelope(seg, sr, rate)
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lo, hi = int(rate * 60 / 150), int(rate * 60 / 118)
    lag = lo + int(np.argmax(ac[lo:hi]))
    return round(60 * rate / lag, 1)


def moments(clean: np.ndarray, sr: int = SR, top: int = 5, before_bars: int = 4,
            after_bars: int = 8) -> list[dict]:
    """The best clips: each drop with its build-up (`before_bars`) and payoff (`after_bars`),
    cut on bar lines (a drop lands on bar 1). Times are in the clean recording."""
    out = []
    for d in find_drops(clean, sr)[:top]:
        bpm = local_bpm(clean, d["time"], sr) or 130.0
        bar = 4 * 60 / bpm
        out.append({"kind": "drop", "at": d["time"], "bpm": bpm, "score": d["score"],
                    "start": round(max(0.0, d["time"] - before_bars * bar), 3),
                    "end": round(d["time"] + after_bars * bar, 3)})
    return out
