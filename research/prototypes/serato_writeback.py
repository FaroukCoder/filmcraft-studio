"""Serato beat grids and cues for whatstheID's own files: anchored, encoded, written safely,
on Windows, for MP3 / WAV / AIFF (ID3 GEOB frames) and FLAC (Vorbis comments).

Three gaps between "whatstheID knows the BPM" and "Serato shows the right grid":
1. **The anchor.** A Serato grid is a BPM *and* a position for a beat. whatstheID's
   `_comb_tempo` already slides a comb over every phase to find the tempo, keeps the best
   score and throws the phase away. `grid_anchor()` runs that comb at the known BPM, then
   finds where each kick's transient starts and fits one straight line through all of them,
   which also corrects the BPM (0.01 BPM off is ~27 ms of drift by the end of a six-minute
   track). It refuses (`ok: false`) when the kicks don't sit on one line. Check it against
   Serato's own grids on your reference tracks (`compare` below) before trusting it.
2. **The bytes.** rb2serato's `seratotags.py` (MIT) encodes `Serato BeatGrid`, `Serato
   Markers2` and `Serato Markers_`; it is loaded from `--rb2serato <path to seratotags.py>`
   (vendor it into whatstheID with its licence notice). FLAC is the hole: neither rb2serato
   nor serato-tools writes Serato tags into FLAC, and FLAC is whatstheID's default format.
   The FLAC layout here follows Holzhaus/serato-tags' format notes (MIT): Vorbis comments
   `SERATO_BEATGRID` / `SERATO_MARKERS_V2`, base64 without padding, a linefeed every 72
   characters, decoding to `application/octet-stream\\0\\0<tag name>\\0<payload>`. It round-trips
   through serato-tools' reader; **it has not been checked against Serato itself.**
3. **The write.** rb2serato's own writer can't run on Windows (it shells out to macOS
   `cp -c`) and its audio check hashes a whole FLAC (so any tag change looks like damage).
   `safe_write()`: copy beside the original, tag the copy, prove the audio bytes are
   identical, then replace. A file Serato holds open fails with "close Serato" and the
   original is untouched.
4. **MP3 timing.** Serato's MP3 timeline is offset from FFmpeg/libmad decoding by roughly
   24-26 ms (Mixxx corrects for it when importing Serato cues). FLAC and WAV need no
   offset. Calibrate MP3s separately with `compare` and pass `--offset-ms`.

    python serato_writeback.py anchor track.flac --bpm 132.0
    python serato_writeback.py write track.flac --rb2serato seratotags.py --cues-only --bpm 132.0 --anchor 0.214 --cue "drop=95.33"
    python serato_writeback.py write track.flac --rb2serato seratotags.py --bpm 132.0 --anchor 0.214 --cue "drop=95.31"
    python serato_writeback.py read track.flac --rb2serato seratotags.py
    python serato_writeback.py compare ours.json serato.json   # anchor error vs Serato, per track

Licence: imports mutagen (GPL-2.0-or-later). Fine inside whatstheID, which already depends
on it and is not distributed; never move this into the FilmCraft fork.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import sys
from pathlib import Path

ID3_EXTS = {".mp3", ".wav", ".aif", ".aiff"}
FLAC_FIELDS = {"Serato BeatGrid": "SERATO_BEATGRID", "Serato Markers2": "SERATO_MARKERS_V2"}
PREFIX = b"application/octet-stream\x00\x00"


class WriteError(RuntimeError):
    pass


# --------------------------------------------------------------------------- 1. anchor

def comb_phase(onset_env, frame_rate: float, bpm: float, phases: int = 400) -> tuple[float, float]:
    """Best phase (seconds, in [0, beat)) of a comb at exactly `bpm` over an onset envelope,
    and its score. Same scoring as whatstheID's `_comb_tempo` (z-scored envelope, linear
    interpolation), just keeping the phase it already computes."""
    import numpy as np

    env = np.asarray(onset_env, dtype=float)
    if env.size < 16 or not (bpm > 0) or not (frame_rate > 0):
        raise ValueError("need an onset envelope and a positive BPM")
    sd = env.std()
    env = (env - env.mean()) / (sd if sd else 1.0)
    n = env.size
    period = 60.0 * frame_rate / bpm
    n_beats = int((n - 1) // period)
    if n_beats < 4:
        raise ValueError("audio too short for this BPM")
    k = np.arange(n_beats)
    best, best_phase = -1e18, 0.0
    for phase in np.linspace(0.0, period, phases, endpoint=False):
        idx = phase + k * period
        i0 = np.floor(idx).astype(int)
        frac = idx - i0
        i1 = np.minimum(i0 + 1, n - 1)
        s = float(np.mean(env[i0] * (1.0 - frac) + env[i1] * frac))
        if s > best:
            best, best_phase = s, float(phase)
    return best_phase / frame_rate, best


def attack_times(y, sr: int, predicted, before: float = 0.06, after: float = 0.045,
                 frac: float = 0.2, cutoff: float = 1000.0):
    """Where each kick actually starts: in a window around each predicted beat, the first
    sample where the zero-phase low-passed envelope reaches `frac` of its rise. Onset
    envelopes peak 18-31 ms after the attack (measured on synthetic kicks, constant with
    tempo); this doesn't. The 1 kHz cutoff keeps the kick's click: a real kick's sub body
    swells for ~20 ms, so a 150 Hz / 50 % rule landed 23 ms late on a recorded loop, while
    1 kHz / 20 % landed 0.9 ms from the transient. Returns (beat_index, time) pairs."""
    import numpy as np
    from scipy.signal import butter, sosfiltfilt

    sos = butter(4, cutoff, btype="low", fs=sr, output="sos")
    env = np.abs(sosfiltfilt(sos, np.asarray(y, dtype=float)))
    w = max(1, int(0.002 * sr))
    env = np.convolve(env, np.ones(w) / w, mode="same")
    floor = float(np.percentile(env, 50))
    out = []
    for k, tb in enumerate(predicted):
        a, b = int((tb - before) * sr), int((tb + after) * sr)
        if a < 0 or b > env.size:
            continue
        seg = env[a:b]
        lo, hi = float(seg.min()), float(seg.max())
        if hi - lo <= floor:  # no kick here (breakdown): skip rather than guess
            continue
        i = int(np.argmax(seg >= lo + frac * (hi - lo)))
        out.append((k, (a + i) / sr))
    return out


def _drift_ms(ks, ts, a: float, P: float, block: int = 16) -> float:
    """Largest |median residual| over blocks of `block` beats, using EVERY detected kick.
    Outlier rejection alone hides a tempo ramp (it drops the beats that disagree and the
    rest fit beautifully: measured, 0.58 ms rms on a +1 BPM/min ramp), so this checks the
    whole track against the line. The search windows cap it near 30 ms, so read anything
    above the limit as "not one tempo", not as a measurement."""
    import numpy as np

    k, t = np.asarray(ks, float), np.asarray(ts, float)
    res = t - (a + k * P)
    worst = 0.0
    for b0 in range(0, int(k.max()) + 1, block):
        sel = (k >= b0) & (k < b0 + block)
        if sel.sum() >= block // 2:
            worst = max(worst, abs(float(np.median(res[sel]))))
    return worst * 1000


def _robust_line(ks, ts):
    """Least-squares t = a + k*P with two rounds of MAD outlier rejection."""
    import numpy as np

    k, t = np.asarray(ks, float), np.asarray(ts, float)
    keep = np.ones(k.size, bool)
    for _ in range(3):
        P, a = np.polyfit(k[keep], t[keep], 1)
        res = t - (a + k * P)
        mad = float(np.median(np.abs(res[keep] - np.median(res[keep])))) or 1e-4
        keep = np.abs(res) <= max(5 * 1.4826 * mad, 0.002)
        if keep.sum() < 8:
            break
    res = t[keep] - (a + k[keep] * P)
    return float(a), float(P), float(np.sqrt(np.mean(res ** 2))), int(keep.sum())


def grid_anchor(y, sr: int, bpm: float, beat_one: int | None = None, hop: int = 512,
                max_rms_ms: float = 4.0, max_drift_ms: float = 5.0, min_kept: float = 0.85) -> dict:
    """A constant-tempo Serato grid for the whole track: anchor time and BPM.

    1. comb phase at the analysed BPM (coarse: lands ~31 ms late at hop 512);
    2. the transient of every kick near that comb, then a straight-line fit of its time
       against beat number over the whole track. The fit corrects the BPM too: a 0.01 BPM
       error is ~27 ms of drift by the end of a six-minute track, which Serato shows.
    3. `beat_one` (0-3, from `downbeat_phase.py` for beats counted from this anchor) moves
       the anchor to a downbeat; the anchor is folded back to the first one at or after 0 s.
    `ok` is False when one straight line doesn't explain the kicks: ragged (rms > max_rms_ms),
    drifting (a 16-beat stretch off the line by > max_drift_ms: a vinyl rip, live drums,
    tempo changes) or mostly rejected (< min_kept of the kicks found). Write nothing then,
    because a precise-looking wrong grid is worse than none."""
    import librosa
    import numpy as np

    y = np.asarray(y, dtype=float)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    phase_s, score = comb_phase(onset, sr / hop, bpm)
    beat = 60.0 / bpm
    dur = y.size / sr
    predicted = np.arange(phase_s, dur, beat)
    hits = attack_times(y, sr, predicted)
    if len(hits) < 16:
        return {"ok": False, "reason": f"only {len(hits)} kicks found", "bpm_in": bpm}
    a, P, rms, used = _robust_line([h[0] for h in hits], [h[1] for h in hits])
    # second pass around the fitted line, so late beats aren't judged against a drifted grid
    predicted = a + np.arange(int((dur - a) / P) + 1) * P
    hits = attack_times(y, sr, predicted, before=0.03, after=0.03)
    if len(hits) >= 16:
        a, P, rms, used = _robust_line([h[0] for h in hits], [h[1] for h in hits])
    drift = _drift_ms([h[0] for h in hits], [h[1] for h in hits], a, P)
    kept = used / max(1, len(hits))
    t = a + (int(beat_one) % 4) * P if beat_one is not None else a
    step = 4 * P if beat_one is not None else P
    t = t - math.floor(t / step) * step
    ok = rms * 1000 <= max_rms_ms and drift <= max_drift_ms and kept >= min_kept
    return {"ok": ok, "anchor_s": round(t, 5), "bpm": round(60.0 / P, 4),
            "bpm_in": bpm, "fit_rms_ms": round(rms * 1000, 2), "drift_ms": round(drift, 2),
            "beats_used": used, "kicks_found": len(hits), "comb_score": round(score, 3),
            "downbeat": beat_one is not None}


def snap_cues(cues: list[dict], anchor_s: float, bpm: float, every_beats: int = 1,
              max_shift_ms: float = 80.0) -> tuple[list[dict], list[dict]]:
    """Move each cue onto the nearest grid line (every beat, or every 4 for bars).

    whatstheID's cues are snapped to librosa's beats, which sit ~25 ms after the kick (its drop
    cue on a recorded loop: 13.47 s against a kick at 13.443 s); a hot cue there starts just
    after the attack. A cue further than max_shift_ms from any line is left alone and
    reported, because it was probably placed on purpose. Returns (cues, moves)."""
    if not (bpm and bpm > 0 and math.isfinite(anchor_s)):
        raise ValueError("snapping needs a grid (anchor and BPM)")
    step = 60.0 / bpm * max(1, int(every_beats))
    out, moves = [], []
    for c in cues or []:
        t = float(c["time"])
        k = round((t - anchor_s) / step)
        g = anchor_s + k * step
        if g >= 0 and abs(g - t) * 1000 <= max_shift_ms:
            out.append({**c, "time": round(g, 4)})
            moves.append({"label": c.get("label", ""), "from": t, "to": round(g, 4), "ms": round((g - t) * 1000, 1)})
        else:
            out.append(dict(c))
            moves.append({"label": c.get("label", ""), "from": t, "to": t, "ms": 0.0, "kept": "no grid line within reach"})
    return out, moves


# --------------------------------------------------------------------------- 2. payloads

def load_seratotags(path: str):
    """Import rb2serato's seratotags.py from a file path (it needs only the stdlib)."""
    spec = importlib.util.spec_from_file_location("seratotags", path)
    if spec is None or spec.loader is None:
        raise WriteError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seratotags"] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


KNOWN_MARKERS2 = {"COLOR", "CUE", "LOOP", "BPMLOCK"}


def markers2_entry_names(raw: bytes) -> list[str]:
    """Entry types inside a Serato Markers2 payload (01 01 + base64 of 01 01 + entries)."""
    body = bytes(raw)[2:].split(b"\x00", 1)[0].replace(b"\n", b"")
    body += b"=" * (-len(body) % 4) if len(body) % 4 != 1 else b"A=="
    inner = base64.b64decode(body)[2:]
    names, off = [], 0
    for _ in range(256):
        end = inner.find(b"\x00", off)
        if end <= off:
            break
        name = inner[off:end].decode("ascii", "replace")
        if end + 5 > len(inner):
            break
        size = struct.unpack(">I", inner[end + 1:end + 5])[0]
        names.append(name)
        off = end + 5 + size
    return names


def merge_cues(st, existing, cues: list[dict] | None, near_ms: int = 250):
    """Your cues and loops stay where they are; new cues go into free slots (0-7), and a new
    cue within `near_ms` of one you already set is skipped. Returns (cues, added, skipped)."""
    kept = list(existing.cues) if existing else []
    used = {c.index for c in kept}
    added, skipped = [], []
    for c in cues or []:
        t = float(c["time"])
        if not (math.isfinite(t) and t >= 0):
            raise ValueError(f"bad cue time {c!r}")
        ms = int(round(t * 1000))
        if any(abs(k.position_ms - ms) <= near_ms for k in kept):
            skipped.append({**c, "why": "you already have a cue there"})
            continue
        free = next((i for i in range(8) if i not in used), None)
        if free is None:
            skipped.append({**c, "why": "all 8 slots are taken"})
            continue
        cue = st.SeratoCue(index=free, position_ms=ms, color=st.DEFAULT_SLOT_COLORS[free],
                           name=str(c.get("label", ""))[:40])
        kept.append(cue)
        used.add(free)
        added.append({"slot": free, "ms": ms, "name": cue.name})
    return sorted(kept, key=lambda c: c.index), added, skipped


def payloads(st, bpm: float | None, anchor_s: float | None, cues: list[dict] | None = None,
             lock: bool = False, existing=None, grid: bool = True) -> dict:
    """{'Serato Markers2': bytes, 'Serato Markers_': bytes, ['Serato BeatGrid': bytes],
    '_added': [...], '_skipped': [...]}. cues: [{"time": s, "label": str}] in seconds.
    `existing` is the file's current SeratoMarkers: its cues, loops, colour and lock are kept.
    grid=False writes cues only and leaves the file's grid alone.

    Refuses anything Serato would choke on rather than writing it."""
    out = {}
    if grid:
        if not (isinstance(bpm, (int, float)) and math.isfinite(bpm) and 40 <= bpm <= 300):
            raise ValueError(f"implausible BPM {bpm!r}")
        if not (isinstance(anchor_s, (int, float)) and math.isfinite(anchor_s) and anchor_s >= 0):
            raise ValueError(f"bad anchor {anchor_s!r}")
        out["Serato BeatGrid"] = st.encode_beatgrid([st.BeatGridMarker(position_sec=float(anchor_s), bpm=float(bpm))])
    merged, added, skipped = merge_cues(st, existing, cues)
    m = st.SeratoMarkers(cues=merged, loops=list(existing.loops) if existing else [],
                         track_color=existing.track_color if existing else st.NO_TRACK_COLOR,
                         bpm_locked=lock if grid else bool(existing and existing.bpm_locked))
    out["Serato Markers2"] = st.encode_markers2_id3(m)
    out["Serato Markers_"] = st.encode_markers_id3(m)
    out["_added"], out["_skipped"] = added, skipped
    return out


def flac_value(name: str, payload: bytes) -> str:
    """Serato's FLAC field value: unpadded base64 of the wrapped payload, 72-char lines."""
    b64 = base64.b64encode(PREFIX + name.encode("ascii") + b"\x00" + payload).rstrip(b"=")
    return b"\n".join(b64[i:i + 72] for i in range(0, len(b64), 72)).decode("ascii")


def flac_unwrap(value: str, name: str) -> bytes:
    s = value.replace("\n", "").replace("\r", "").encode("ascii")
    s += b"=" * (-len(s) % 4)
    data = base64.b64decode(s)
    head = PREFIX + name.encode("ascii") + b"\x00"
    if not data.startswith(head):
        raise ValueError(f"not a Serato {name} field")
    return data[len(head):]


# --------------------------------------------------------------------------- 3. safe write

def _flac_audio_start(data: bytes) -> int:
    if data[:4] != b"fLaC":
        raise WriteError("not a FLAC file")
    off = 4
    for _ in range(1024):  # metadata blocks: 1-bit last flag, 7-bit type, 24-bit length
        if off + 4 > len(data):
            raise WriteError("truncated FLAC metadata")
        last = data[off] & 0x80
        size = int.from_bytes(data[off + 1:off + 4], "big")
        off += 4 + size
        if last:
            return off
    raise WriteError("too many FLAC metadata blocks")


def _chunk(data: bytes, name: bytes, start: int, big: bool) -> bytes:
    off, fmt = start, (">4sI" if big else "<4sI")
    while off + 8 <= len(data):
        cid, size = struct.unpack(fmt, data[off:off + 8])
        if cid == name:
            return data[off + 8:off + 8 + size]
        off += 8 + size + (size & 1)
    raise WriteError(f"no {name.decode()} chunk")


def audio_digest(path: str | Path) -> str:
    """SHA-256 of the audio payload only, so tags can change and the music provably can't."""
    p = Path(path)
    data = p.read_bytes()
    ext = p.suffix.lower()
    if ext == ".flac":
        body = data[_flac_audio_start(data):]
    elif ext == ".mp3":
        start = 0
        if data[:3] == b"ID3" and len(data) >= 10:
            size = (data[6] & 0x7F) << 21 | (data[7] & 0x7F) << 14 | (data[8] & 0x7F) << 7 | (data[9] & 0x7F)
            start = 10 + size + (10 if data[5] & 0x10 else 0)
        body = data[start:]
        if body[-128:-125] == b"TAG":
            body = body[:-128]
        body = body.lstrip(b"\x00")  # tag padding
    elif ext == ".wav":
        body = _chunk(data, b"data", 12, big=False)
    elif ext in (".aif", ".aiff"):
        body = _chunk(data, b"SSND", 12, big=True)
    else:
        raise WriteError(f"unsupported file type {ext}")
    return hashlib.sha256(body).hexdigest()


def _tag_file(path: str, tags: dict) -> None:
    ext = Path(path).suffix.lower()
    if ext == ".flac":
        from mutagen.flac import FLAC

        f = FLAC(path)
        if f.tags is None:
            f.add_tags()
        for name, field in FLAC_FIELDS.items():
            if name in tags:
                f.tags[field] = [flac_value(name, tags[name])]
        f.save()
        return
    if ext in ID3_EXTS:
        from mutagen.id3 import GEOB

        if ext == ".mp3":
            from mutagen.mp3 import MP3 as Kind
        elif ext == ".wav":
            from mutagen.wave import WAVE as Kind
        else:
            from mutagen.aiff import AIFF as Kind
        f = Kind(path)
        if f.tags is None:
            f.add_tags()
        for name, data in tags.items():
            f.tags.delall(f"GEOB:{name}")
            f.tags.add(GEOB(encoding=0, mime="application/octet-stream", desc=name, data=data))
        f.save()
        return
    raise WriteError(f"unsupported file type {ext}")


def safe_write(path: str | Path, mutate, backup_dir: str | Path | None = None) -> dict:
    """Copy -> mutate(copy) -> prove the audio is byte-identical -> replace the original.
    Optionally keeps the untouched original in backup_dir first (do, for the first runs)."""
    p = Path(path)
    if not p.is_file():
        raise WriteError(f"no such file: {p}")
    tmp = p.with_name(p.stem + ".serato-tmp" + p.suffix)  # keep the extension for mutagen
    before = audio_digest(p)
    shutil.copy2(p, tmp)
    try:
        mutate(str(tmp))
        if audio_digest(tmp) != before:
            raise WriteError("audio payload changed while writing tags; original left untouched")
        if backup_dir:
            Path(backup_dir).mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, Path(backup_dir) / p.name)
        try:
            os.replace(tmp, p)
        except PermissionError as e:  # Windows: Serato (or a player) has the file open
            raise WriteError(f"{p.name} is open in another program; close Serato and retry") from e
    finally:
        if tmp.exists():
            tmp.unlink()
    return {"path": str(p), "audio_sha256": before}


def raw_tags(path: str) -> dict:
    """{'Serato BeatGrid': bytes, 'Serato Markers2': bytes, ...} as stored in the file now."""
    ext = Path(path).suffix.lower()
    raw = {}
    if ext == ".flac":
        from mutagen.flac import FLAC

        t = FLAC(path).tags or {}
        for name, field in FLAC_FIELDS.items():
            if field in t:
                raw[name] = flac_unwrap(t[field][0], name)
    else:
        from mutagen import File

        f = File(path)
        for fr in (f.tags.getall("GEOB") if f is not None and f.tags is not None else []):
            raw[fr.desc] = bytes(fr.data)
    return raw


def write(path: str, st, bpm: float | None, anchor_s: float | None, cues=None, lock: bool = False,
          backup_dir=None, offset_ms: float = 0.0, grid: bool = True, snap: bool = True) -> dict:
    """Add cues (and, with grid=True, a grid) without losing what you set in Serato.

    Your existing cues, loops, track colour and BPM lock are kept; new cues fill free slots.
    A Markers2 tag holding entry types this can't re-encode (e.g. Flip) is refused, because
    rewriting it would drop them. offset_ms shifts the grid and cues onto Serato's timeline:
    0 for FLAC and WAV; for MP3, Serato and FFmpeg/libmad decoders disagree by roughly 24-26
    ms (Mixxx applies -26 ms at 44.1 kHz and -24 ms at 48 kHz when importing Serato cues, and
    other values under Core Audio), so measure yours with `compare` on MP3s Serato analysed."""
    moves = []
    if snap and cues and bpm and anchor_s is not None:
        cues, moves = snap_cues(cues, anchor_s, bpm)  # onto the grid before any offset is applied
    if offset_ms:
        if grid and anchor_s is not None:
            anchor_s = anchor_s + offset_ms / 1000.0
            beat = 60.0 / bpm if bpm and bpm > 0 else 0
            if beat and anchor_s < 0:
                anchor_s += math.ceil(-anchor_s / beat) * beat
        cues = [{**c, "time": max(0.0, float(c["time"]) + offset_ms / 1000.0)} for c in (cues or [])]
    existing = None
    raw = raw_tags(path).get("Serato Markers2")
    if raw:
        try:
            names = markers2_entry_names(raw)
            existing = st.decode_markers2(raw)
        except Exception as e:  # noqa: BLE001 - an unreadable tag is never overwritten blind
            raise WriteError(f"can't read the existing Serato cues in {Path(path).name}; not touching it") from e
        unknown = sorted(set(names) - KNOWN_MARKERS2)
        if unknown:
            raise WriteError(f"{Path(path).name} has Serato data this can't keep ({', '.join(unknown)}); not touching it")
    tags = payloads(st, bpm, anchor_s, cues, lock, existing=existing, grid=grid)
    added, skipped = tags.pop("_added"), tags.pop("_skipped")
    if Path(path).suffix.lower() == ".flac":
        tags.pop("Serato Markers_")  # no FLAC field for it in the format notes
    res = safe_write(path, lambda t: _tag_file(t, tags), backup_dir)
    return {**res, "cues_added": added, "cues_skipped": skipped, "cue_moves": moves, "grid_written": grid}


def read(path: str, st) -> dict:
    """Decode what is in the file now with rb2serato's decoders (for checking a write)."""
    raw = raw_tags(path)
    out = {}
    if "Serato BeatGrid" in raw:
        g = st.decode_beatgrid(raw["Serato BeatGrid"])
        out["grid"] = [{"position_s": m.position_sec, "bpm": m.bpm, "beats_to_next": m.beats_to_next} for m in g]
    if "Serato Markers2" in raw:
        m = st.decode_markers2(raw["Serato Markers2"])
        out["cues"] = [{"slot": c.index, "ms": c.position_ms, "name": c.name} for c in m.cues]
        out["loops"] = [{"slot": lp.index, "start_ms": lp.start_ms, "end_ms": lp.end_ms} for lp in m.loops]
        out["track_color"] = list(m.track_color)
        out["bpm_locked"] = m.bpm_locked
    return out


# --------------------------------------------------------------------------- calibration

def compare(ours: dict, serato: dict) -> dict:
    """Anchor error against Serato's own grids: {track: {"bpm", "anchor_s"}} each (read
    Serato's with `read` on tracks Serato analysed). Errors are folded to the nearest beat,
    so they measure phase, not which beat was picked; a constant mean is a bias to correct."""
    rows = []
    for k, o in ours.items():
        s = serato.get(k)
        if not s or not s.get("bpm"):
            continue
        beat = 60.0 / float(s["bpm"])
        d = (float(o["anchor_s"]) - float(s["anchor_s"])) % beat
        d = d - beat if d > beat / 2 else d
        rows.append({"track": k, "error_ms": round(d * 1000, 1), "bpm_diff": round(float(o["bpm"]) - float(s["bpm"]), 3)})
    errs = sorted(r["error_ms"] for r in rows)
    mean = sum(errs) / len(errs) if errs else None
    return {"n": len(rows), "mean_error_ms": round(mean, 1) if mean is not None else None,
            "median_error_ms": errs[len(errs) // 2] if errs else None,
            "within_10ms_after_lag": sum(abs(e - mean) <= 10 for e in errs) if errs else 0, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("anchor")
    a.add_argument("audio")
    a.add_argument("--bpm", type=float, required=True)
    a.add_argument("--beat-one", type=int)
    w = sub.add_parser("write")
    w.add_argument("audio")
    w.add_argument("--rb2serato", required=True, help="path to rb2serato's seratotags.py")
    w.add_argument("--bpm", type=float)
    w.add_argument("--anchor", type=float)
    w.add_argument("--cues-only", action="store_true", help="add cues, leave the file's grid alone")
    w.add_argument("--no-snap", action="store_true", help="don't move cues onto the grid (given --bpm and --anchor)")
    w.add_argument("--cue", action="append", default=[], help="label=seconds")
    w.add_argument("--lock", action="store_true")
    w.add_argument("--backup-dir")
    w.add_argument("--offset-ms", type=float, default=0.0, help="MP3 only: decoder-vs-Serato offset from `compare`")
    r = sub.add_parser("read")
    r.add_argument("audio")
    r.add_argument("--rb2serato", required=True)
    c = sub.add_parser("compare")
    c.add_argument("ours")
    c.add_argument("serato")
    args = ap.parse_args(argv)
    if args.cmd == "anchor":
        import librosa

        y, sr = librosa.load(args.audio, sr=22050, mono=True)
        print(json.dumps(grid_anchor(y, sr, args.bpm, beat_one=args.beat_one)))
    elif args.cmd == "write":
        cues = [{"label": s.split("=", 1)[0], "time": float(s.split("=", 1)[1])} for s in args.cue]
        if not args.cues_only and (args.bpm is None or args.anchor is None):
            ap.error("--bpm and --anchor are required unless --cues-only")
        print(json.dumps(write(args.audio, load_seratotags(args.rb2serato), args.bpm, args.anchor, cues,
                               args.lock, args.backup_dir, args.offset_ms, grid=not args.cues_only,
                               snap=not args.no_snap)))
    elif args.cmd == "read":
        print(json.dumps(read(args.audio, load_seratotags(args.rb2serato)), indent=2))
    else:
        print(json.dumps(compare(json.load(open(args.ours)), json.load(open(args.serato))), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
