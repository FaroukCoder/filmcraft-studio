"""Talking-head analysis: Whisper word timestamps (CPU) -> speech segments without silences
and filler words. Cached next to the job so re-edits (v2, v3) don't re-transcribe."""
from __future__ import annotations

import functools
import json
import re
import subprocess
from pathlib import Path

WHISPER_MODEL, WHISPER_DIR = "small.en", r"E:\AI\reels\models"  # shared with Reel Brain
FILLERS = {"um", "uh", "erm", "er", "uhm", "hmm", "mm", "ah"}  # never "like"/"so": often real words


@functools.cache
def _whisper():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", download_root=WHISPER_DIR)


def probe(video: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s, num_den = j["streams"][0], j["streams"][0]["r_frame_rate"].split("/")
    return {"width": s["width"], "height": s["height"], "duration": float(j["format"]["duration"]),
            "fps": round(float(num_den[0]) / float(num_den[1] or 1), 3)}


def words(video: Path, cache: Path) -> list[dict]:
    """[{"w": "hello", "start": 0.12, "end": 0.40}, ...] in source seconds."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "s16le", "-ac", "1",
                          "-ar", "16000", "-"], capture_output=True).stdout
    out: list[dict] = []
    if pcm:
        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        segs, _ = _whisper().transcribe(audio, word_timestamps=True, vad_filter=True)
        out = [{"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
               for s in segs for w in (s.words or []) if w.word.strip()]
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def is_filler(word: str) -> bool:
    return re.sub(r"[^a-z]", "", word.lower()) in FILLERS


def speech_segments(ws: list[dict], max_gap: float = 0.35, pad: float = 0.08,
                    min_len: float = 0.3, duration: float | None = None) -> list[tuple[float, float]]:
    """Source-time (start, end) spans to keep: runs of non-filler words whose gaps are under
    `max_gap`, padded by `pad` (so words aren't clipped) and merged where padding overlaps."""
    spans: list[list[float]] = []
    for w in ws:
        if is_filler(w["w"]):
            continue
        if spans and w["start"] - spans[-1][1] <= max_gap:
            spans[-1][1] = w["end"]
        else:
            spans.append([w["start"], w["end"]])
    out: list[list[float]] = []
    for a, b in spans:
        a, b = max(0.0, a - pad), b + pad
        if duration:
            b = min(b, duration)
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in out if b - a >= min_len]
