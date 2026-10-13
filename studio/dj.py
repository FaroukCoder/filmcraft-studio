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
FINE_S = 1.5  # sync: the waveform search reaches this far either side of the coarse guess
SYNC_MIN_CONF = 15  # below this, refuse: true matches score 24+, other recordings <= 5, pure loops ~11


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


def _env_rate(sr: int, rate: int = 200) -> float:
    """The envelope's true sample rate: hops are whole samples, so 11025 // 200 = 55 gives
    200.45 Hz, not 200. Using 200 made every tempo ~0.23% slow and the sync's coarse offset
    drift ~0.14 s per minute of offset (past the fine search's 0.3 s after ~2 min)."""
    return sr / (sr // rate)


def _xcorr(a: np.ndarray, b: np.ndarray, phat: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Cross-correlation of a against b for every lag (a[t + lag] ~ b[t]). `phat`: GCC-PHAT
    (whitened spectrum), which keeps the direct-sound peak sharp when the camera hears a
    reverberant room; plain correlation can lock onto a reflection (~70 ms early in a wet room)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    x = np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n))
    if phat:
        x /= np.abs(x) + 1e-12
    xc = np.fft.irfft(x, n)
    lags = np.r_[np.arange(0, len(a)), np.arange(-len(b) + 1, 0)]
    return np.r_[xc[: len(a)], xc[n - len(b) + 1:]], lags


def _loudness(y: np.ndarray, sr: int, rate: int = 20) -> np.ndarray:
    """Log loudness at `rate` Hz: the song's shape (breakdowns, drops, transitions), which unlike
    the beat-level onset envelope doesn't repeat every bar."""
    hop = sr // rate
    n = len(y) // hop
    return np.log(np.square(y[: n * hop]).reshape(n, hop).mean(axis=1) + 1e-8)


def sync_offset(clean: np.ndarray, camera: np.ndarray, sr: int = SR, max_lag: float | None = None,
                rate: int = 20) -> tuple[float, float]:
    """Seconds into the clean recording at which the camera's recording starts, and a
    confidence. Coarse: the loudness envelope at `rate` Hz (song structure: breakdowns,
    drops, mixes) matched by normalised correlation finds the place. Beat-level envelopes can't:
    techno repeats every beat, so positions whole bars apart look alike, and raw correlation
    also favours the loudest stretch of the set. Fine: the raw waveforms around it (+-0.3 s)
    give sample precision. The confidence is how far the coarse peak stands above the typical
    correlation. The confidence is the GCC-PHAT peak-to-sidelobe ratio: real-set benchmark, phone-mic
    simulation: true matches 24+, a camera from another recording <= 5. `max_lag` (s) bounds the
    search; default: anywhere."""
    a, b = _loudness(clean, sr, rate), _loudness(camera, sr, rate)
    b = (b - b.mean()) / (b.std() + 1e-9)
    xc, lags = _xcorr(a, b)
    rate = _env_rate(sr, rate)
    # the camera must lie (90%) inside the recording: partial overlaps at the edges correlate
    # over a few seconds only and spike (they won every miss in the real-set benchmark)
    ok = (lags >= 0) & (lags + int(0.9 * len(b)) <= len(a))
    if max_lag is not None:
        ok &= lags <= max_lag * rate
    xc, lags = xc[ok], lags[ok]
    # Pearson correlation per lag: divide by the recording's local spread under the camera
    n = np.minimum(len(b), len(a) - lags)
    s1, s2 = np.r_[0.0, np.cumsum(a)], np.r_[0.0, np.cumsum(a.astype(np.float64) ** 2)]
    mean = (s1[lags + n] - s1[lags]) / n
    sd = np.sqrt(np.maximum((s2[lags + n] - s2[lags]) / n - mean ** 2, 1e-12))
    xc = xc / (n * sd)
    best = int(np.argmax(xc))
    z = (xc[best] - np.median(xc)) / (xc.std() + 1e-9)
    coarse = lags[best] / rate
    # fine: the raw waveform within +-FINE_S of the coarse guess. Loudness pins the section but
    # kick pulses blur it by up to a beat, and inside one loop the waveform repeats every bar,
    # so match the 20 s of camera with the most going on (largest loudness spread: a breakdown,
    # a drop, a mix), where only one alignment fits.
    seg_n = min(len(b), int(20 * rate))
    spread = [b[i:i + seg_n].std() for i in range(0, max(1, len(b) - seg_n + 1), int(rate))]
    seg0 = int(int(np.argmax(spread)) * int(rate) / rate * sr)
    cam = camera[seg0: seg0 + 20 * sr]
    c0 = int((coarse + seg0 / sr - FINE_S) * sr)
    if c0 < 0 or c0 + len(cam) + int(2 * FINE_S * sr) > len(clean):
        return round(coarse, 3), round(float(z), 1)
    ref = clean[c0: c0 + len(cam) + int(2 * FINE_S * sr)]
    fx, flags = _xcorr(ref - ref.mean(), cam - cam.mean(), phat=True)
    good = (flags >= 0) & (flags <= int(2 * FINE_S * sr))
    win, lags_w = fx[good], flags[good]
    i = int(np.argmax(win))
    # confidence = how far the PHAT peak stands above the rest of the window (peak-to-sidelobe):
    # a true match is one sharp spike; a camera from another recording is noise everywhere
    side = np.r_[win[: max(0, i - 50)], win[i + 51:]]
    psr = (win[i] - side.mean()) / (side.std() + 1e-12)
    return round((c0 + lags_w[i]) / sr - seg0 / sr, 4), round(float(psr), 1)


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
    level = np.array([np.percentile(pad[i:i + w], 75) for i in range(len(e))])
    # floor: a quarter of the set's typical bass. Near a quiet intro the 60 s window holds no
    # full-volume music, so a soft intro kick would count as "loud" (the real set's 0:32)
    level = np.maximum(level, 0.25 * np.median(e)) + 1e-12
    r = e / level
    nb, na = int(before / WIN), int(after / WIN)
    cs = np.r_[0, np.cumsum(r)]
    cand = []
    for i in range(nb, len(r) - na):
        pre = (cs[i - 1] - cs[i - nb]) / (nb - 1)  # leave out the frame the smoothing leaks into
        post = (cs[i + na + 1] - cs[i + 2]) / (na - 1)
        # the bass must STAY back: the median, not just the mean, of the after-window (a lone boom
        # in a quiet intro lifts the mean for a second; the real set opened like that at 0:32)
        if pre < max_before and post > min_after and np.median(r[i + 2:i + na + 1]) > min_after:
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


def _peak(ac: np.ndarray, i: int) -> float:
    """Sub-sample position of the autocorrelation peak at index i (parabola through 3 points)."""
    y0, y1, y2 = ac[i - 1], ac[i], ac[i + 1]
    d = y0 - 2 * y1 + y2
    return i + (0.5 * (y0 - y2) / d if d else 0.0)


def local_bpm(y: np.ndarray, at: float, sr: int = SR, span: float = 16.0,
              lo_bpm: float = 115, hi_bpm: float = 165) -> float | None:
    """Tempo right after `at` from the autocorrelation of the onset envelope. The beat lag gives
    the tempo; the one-bar lag (4 beats), refined to a fraction of a sample, gives the precision:
    a whole-sample beat lag at 200 Hz is up to 0.3% off, which puts a cut 8 bars before the drop
    ~40 ms off the downbeat (audible). Range 115-165 BPM covers house to hard techno."""
    seg = y[int(at * sr): int((at + span) * sr)]
    if len(seg) < sr * 6:
        return None
    env = _envelope(seg, sr, 200)
    rate = _env_rate(sr, 200)
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lo, hi = int(rate * 60 / hi_bpm), int(rate * 60 / lo_bpm) + 1
    beat = lo + int(np.argmax(ac[lo:hi]))
    b4 = 4 * beat  # the bar lag: search +-3 samples around 4 beats for its true peak
    if b4 + 4 >= len(ac):
        return round(float(60 * rate / _peak(ac, beat)), 2)
    i = b4 - 3 + int(np.argmax(ac[b4 - 3:b4 + 4]))
    return round(float(4 * 60 * rate / _peak(ac, i)), 2)


def moments(clean: np.ndarray, sr: int = SR, top: int = 5, before_bars: int = 4,
            after_bars: int = 8) -> list[dict]:
    """The best clips: each drop with its build-up (`before_bars`) and payoff (`after_bars`),
    cut on bar lines (a drop lands on bar 1). Times are in the clean recording.
    Tempo is read 3 times (0, 4, 8 s after the drop). If the reads disagree by > 1.5 BPM (a
    transition or syncopated kicks: one real-set drop read anywhere from 123 to 163), the set's
    tempo from the stable drops is used instead and `bpm_sure` is False."""
    drops = find_drops(clean, sr)[:top]
    reads = [[b for b in (local_bpm(clean, d["time"] + o, sr) for o in (0, 4, 8)) if b] for d in drops]
    sure = [bool(len(r) == 3 and max(r) - min(r) <= 1.5) for r in reads]
    stable = sorted(float(np.median(r)) for r, ok in zip(reads, sure) if ok)
    set_bpm = stable[len(stable) // 2] if stable else 130.0
    out = []
    for d, r, ok in zip(drops, reads, sure):
        bpm = round(float(np.median(r)), 2) if ok else set_bpm
        bar = 4 * 60 / bpm
        out.append({"kind": "drop", "at": d["time"], "bpm": bpm, "bpm_sure": ok, "score": d["score"],
                    "break": d["break"], "start": round(max(0.0, d["time"] - before_bars * bar), 3),
                    "end": round(d["time"] + after_bars * bar, 3)})
    return out
