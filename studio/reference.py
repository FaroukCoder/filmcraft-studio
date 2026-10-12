"""Reference analyzer -> style packs (master plan P3, Q10).

Measures reference videos (cut rhythm, caption look, picture look, speech rate) and writes a
style pack the planner follows: vault Styles/<name>.md, a readable note with a ```json block.

    python -m studio.reference <style-name> <video-or-reel-code> [...]"""
from __future__ import annotations

import functools
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

from . import analyze

VAULT_STYLES = Path(r"C:\Users\Administrator\ClaudeRook\ObsidianWIki\Styles")
REELS_MEDIA = Path(r"E:\AI\reels\media")
CACHE = Path(r"E:\AI\studio-jobs\_references")


def resolve(ref: str) -> Path:
    """A file path, or a Reel Brain shortcode (its downloaded video)."""
    p = Path(ref)
    return p if p.exists() else REELS_MEDIA / ref / "video.mp4"


def cuts(video: Path, threshold: float = 0.3) -> list[float]:
    """Scene-change timestamps (seconds)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                        f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def look(video: Path) -> dict:
    """Average brightness (0-255) and saturation from ffmpeg signalstats at 2 fps."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                        "fps=2,scale=270:-2,signalstats,metadata=print", "-f", "null", "-"],
                       capture_output=True, text=True)
    y = [float(v) for v in re.findall(r"signalstats\.YAVG=([\d.]+)", r.stderr)]
    s = [float(v) for v in re.findall(r"signalstats\.SATAVG=([\d.]+)", r.stderr)]
    return {"brightness": round(statistics.mean(y), 1) if y else None,
            "saturation": round(statistics.mean(s), 1) if s else None}


@functools.cache
def _ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()


def caption_look(video: Path, info: dict, samples: int = 24) -> dict:
    """Sample frames, OCR the lower 3/4 of the picture (where captions live) and measure how
    often text is on screen, how many words show at once, case and vertical position."""
    hits, words, upper, ys = 0, [], [], []
    tmp = CACHE / "_frame.jpg"
    for i in range(samples):
        t = info["duration"] * (i + 0.5) / samples
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(tmp)], check=True)
        res, _ = _ocr()(str(tmp))
        lines = [(box, text) for box, text, conf in (res or []) if float(conf) >= 0.8 and len(text.strip()) >= 2]
        h = 540 * info["height"] / info["width"]  # frames are scaled to 540 wide
        lines = [(b, t) for b, t in lines if (b[0][1] + b[2][1]) / 2 > h * 0.25]  # skip top UI/titles
        if not lines:
            continue
        hits += 1
        biggest = max(lines, key=lambda bt: bt[0][2][1] - bt[0][0][1])  # tallest text = the caption
        words.append(len(biggest[1].split()))
        letters = [c for c in biggest[1] if c.isalpha()]
        upper.append(sum(c.isupper() for c in letters) / len(letters) if letters else 0)
        ys.append(((biggest[0][0][1] + biggest[0][2][1]) / 2) / h)
    return {"caption_frames": round(hits / samples, 2),
            "words_per_caption": round(statistics.median(words), 1) if words else None,
            "uppercase": round(statistics.mean(upper), 2) if upper else None,
            "caption_y": round(statistics.median(ys), 2) if ys else None}


def p90_word_gap(ws: list[dict]) -> float | None:
    """The pauses the editor left in: 90th percentile of gaps between words (under 2 s)."""
    gaps = sorted(b["start"] - a["end"] for a, b in zip(ws, ws[1:]) if 0 <= b["start"] - a["end"] < 2)
    return round(gaps[int(len(gaps) * 0.9)], 3) if len(gaps) >= 10 else None


def measure(ref: str) -> dict:
    video = resolve(ref)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{re.sub(r'[^\w-]', '_', ref)[-60:]}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    info = analyze.probe(video)
    c = cuts(video)
    ws = analyze.words(video, CACHE / f"{cache.stem}.words.json")
    m = {"ref": ref, "duration": round(info["duration"], 1),
         "cuts_per_10s": round(len(c) / info["duration"] * 10, 2),
         "median_shot": round(statistics.median([b - a for a, b in zip([0, *c], [*c, info["duration"]])]), 2),
         "words_per_second": round(len(ws) / info["duration"], 2),
         "p90_word_gap": p90_word_gap(ws),
         **look(video), **caption_look(video, info)}
    cache.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return m


def to_style(ms: list[dict]) -> dict:
    """Turn the references' medians into planner parameters (plan.STYLES schema)."""
    med = lambda k: statistics.median([m[k] for m in ms if m.get(k) is not None]) if any(  # noqa: E731
        m.get(k) is not None for m in ms) else None
    pace, wpc, up, y = med("cuts_per_10s"), med("words_per_caption"), med("uppercase"), med("caption_y")
    gap, wps = med("p90_word_gap"), med("words_per_second")
    # cut as tightly as the references do: scene detection misses talking-head jump cuts (same
    # framing), so the pauses they left between words are the reliable pace signal
    if gap is not None:
        max_gap = min(0.6, max(0.15, round(gap + 0.1, 2)))
    else:
        max_gap = 0.25 if pace and pace >= 5 else 0.5 if pace is not None and pace < 2 else 0.35
    fast = (pace is not None and pace >= 5) or (wps is not None and wps >= 3.5)
    anchor = "top" if y is not None and y < 0.4 else "bottom" if y is not None and y > 0.72 else "middle"
    return {"max_gap": max_gap, "pad": 0.08, "punch_in": 1.15 if fast else 1.12,
            "min_zoom_len": 0.6 if fast else 0.8,
            "words_per_caption": max(1, min(4, round(wpc))) if wpc else 3,
            "chars_per_caption": 18, "uppercase": bool(up is not None and up >= 0.6),
            "caption_style": {"font": "Inter", "size": 84, "color": "#ffffff", "background": False,
                              "outline": 6.0, "outlineColor": "#000000", "align": "center",
                              "anchor": anchor, "margin": 0.18 if anchor != "middle" else 0.0},
            "measured": {k: med(k) for k in ("cuts_per_10s", "median_shot", "words_per_second",
                                             "brightness", "saturation", "caption_frames",
                                             "words_per_caption", "uppercase", "caption_y",
                                             "p90_word_gap")}}


def write_pack(name: str, refs: list[str]) -> Path:
    ms = [measure(r) for r in refs]
    style = to_style(ms)
    VAULT_STYLES.mkdir(parents=True, exist_ok=True)
    path = VAULT_STYLES / f"{name}.md"
    m = style["measured"]
    path.write_text(
        "---\ntype: style-pack\n---\n"
        f"# {name}\n\nBuilt from {len(refs)} reference(s): "
        + ", ".join(f"[[Reels/{r}]]" if not Path(r).exists() else r for r in refs) + ".\n\n"
        f"- Pace: {m['cuts_per_10s']} cuts/10s (median shot {m['median_shot']}s)\n"
        f"- Speech: {m['words_per_second']} words/s; pauses left in (p90): {m['p90_word_gap']}s, "
        f"so cut pauses over {style['max_gap']}s\n"
        f"- Captions: on screen {m['caption_frames']:.0%} of the time, {m['words_per_caption']} words at a time, "
        f"{'UPPERCASE' if style['uppercase'] else 'mixed case'}, {style['caption_style']['anchor']}\n"
        f"- Look: brightness {m['brightness']}, saturation {m['saturation']}\n\n"
        "Edit the JSON below to tweak the pack; the planner reads it.\n\n"
        "```json\n" + json.dumps({k: v for k, v in style.items() if k != "measured"}, indent=1) + "\n```\n",
        encoding="utf-8")
    return path


def load_pack(name: str) -> dict | None:
    """A style pack from the vault (None if missing)."""
    p = VAULT_STYLES / f"{name}.md"
    if not p.exists():
        return None
    m = re.search(r"```json\n(.*?)\n```", p.read_text(encoding="utf-8"), re.S)
    return json.loads(m[1]) if m else None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    print(write_pack(sys.argv[1], sys.argv[2:]))
