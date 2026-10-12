"""Edit Decision List (EDL) planning. v1 is rule-based (the "talking-head default" style from
the master plan); the local-LLM planner will write the same EDL schema once the GPU is stable.

EDL v1 schema:
{"version": 1, "style": str, "source": path, "size": [w, h], "fps": f,
 "segments": [{"src_in": s, "src_out": s, "start": s, "zoom": 1.0}],   # start = timeline s
 "captions": [{"start": s, "end": s, "text": str}],                     # timeline seconds
 "caption_style": {...}, "base_scale": percent}"""
from __future__ import annotations

import re

STYLES = {
    "talking-head-default": {
        "max_gap": 0.35, "pad": 0.08, "punch_in": 1.12, "min_zoom_len": 0.8,
        "words_per_caption": 3, "chars_per_caption": 18, "uppercase": True,
        "caption_style": {"font": "Inter", "size": 84, "color": "#ffffff", "background": False,
                          "outline": 6.0, "outlineColor": "#000000",  # readable on any footage
                          "align": "center", "anchor": "middle", "margin": 0.18},
    },
}


def get_style(name: str) -> dict:
    """A built-in style, else a style pack from the vault (Styles/<name>.md)."""
    if name in STYLES:
        return STYLES[name]
    from .reference import load_pack
    pack = load_pack(name)
    if pack is None:
        raise KeyError(f"unknown style {name!r}: not built in and no Styles/{name}.md in the vault")
    return pack


def base_scale(src_w: int, src_h: int, out_w: int = 1080, out_h: int = 1920) -> float:
    """Motion scale (%) that fills the vertical frame (centre crop) from any source shape."""
    return round(max(out_w / src_w, out_h / src_h) * 100, 2)


def caption_chunks(ws: list[dict], max_words: int, max_chars: int) -> list[list[dict]]:
    """Group words into short captions, breaking early after sentence punctuation."""
    chunks: list[list[dict]] = []
    cur: list[dict] = []
    for w in ws:
        text = " ".join(x["w"] for x in cur + [w])
        if cur and (len(cur) >= max_words or len(text) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,]$", w["w"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def frame_snap(caps: list[dict], fps: float) -> list[dict]:
    """FilmCraft snaps caption times to whole frames, so two captions touching in seconds can
    collide after rounding ("a caption already covers this time"). Snap here, then make each
    caption end no later than the next one starts and keep only those at least a frame long."""
    for c in caps:
        c["f0"], c["f1"] = round(c["start"] * fps), round(c["end"] * fps)
    for a, b in zip(caps, caps[1:]):
        a["f1"] = min(a["f1"], b["f0"])
    return [{"start": round(c["f0"] / fps, 4), "end": round(c["f1"] / fps, 4), "text": c["text"]}
            for c in caps if c["f1"] > c["f0"]]


def plan_talking_head(source: str, info: dict, ws: list[dict], segments: list[tuple[float, float]],
                      style: str = "talking-head-default") -> dict:
    st = get_style(style)
    segs, t, zoomed = [], 0.0, False
    for a, b in segments:
        if b - a >= st["min_zoom_len"]:
            zoomed = not zoomed  # alternate framing on every real cut: the jump-cut punch-in
        segs.append({"src_in": a, "src_out": b, "start": round(t, 3),
                     "zoom": st["punch_in"] if zoomed else 1.0})
        t += b - a
    caps = []
    for s in segs:  # map the words inside each kept span onto the timeline
        inside = [w for w in ws if w["start"] >= s["src_in"] and w["end"] <= s["src_out"]
                  and not re.fullmatch(r"\W*(um|uh|erm|er|uhm|hmm|mm|ah)\W*", w["w"].lower())]
        off = s["start"] - s["src_in"]
        seg_end = s["start"] + s["src_out"] - s["src_in"]
        for ch in caption_chunks(inside, st["words_per_caption"], st["chars_per_caption"]):
            text = " ".join(w["w"] for w in ch)
            caps.append({"start": round(ch[0]["start"] + off, 3),
                         "end": round(min(ch[-1]["end"] + off + 0.1, seg_end), 3),
                         "text": text.upper() if st["uppercase"] else text})
    caps = frame_snap(caps, fps=30)
    return {"version": 1, "style": style, "source": source, "size": [1080, 1920],
            "fps": 30, "segments": segs, "captions": caps,
            "caption_style": st["caption_style"],
            "base_scale": base_scale(info["width"], info["height"])}
