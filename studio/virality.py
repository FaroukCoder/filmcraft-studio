"""Virality rubric v1 (master plan Q19): each item scored 0-10. The measurable items come from
the EDL and the render; items that need judgement (payoff/loop) stay None until the LLM
judge exists. The total is the mean of the scored items, so a missing judge doesn't sink it."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

PLATFORM_SWEET_SPOT = {"instagram": (15, 45), "tiktok": (21, 34), "youtube": (15, 58)}
TARGET_LUFS, CUTS_PER_10S = -14.0, (2.5, 6.0)  # talking-head pace window (cuts + punch-ins)
CTA = re.compile(r"\?|\b(comment|follow|save this|share|link in bio|id\b|which one|thoughts)", re.I)


def _band(x: float, lo: float, hi: float, soft: float) -> float:
    """10 inside [lo, hi], falling linearly to 0 at `soft` outside it."""
    if lo <= x <= hi:
        return 10.0
    d = lo - x if x < lo else x - hi
    return round(max(0.0, 10 * (1 - d / soft)), 1)


def loudness(video: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def score(edl: dict, render: Path | None = None, platform: str = "instagram") -> dict:
    caps, segs = edl.get("captions", []), edl.get("segments", [])
    dur = (segs[-1]["start"] + segs[-1]["src_out"] - segs[-1]["src_in"]) if segs else 0.0
    items: dict[str, dict] = {}

    first_word = caps[0]["start"] if caps else dur
    early_cut = any(0 < s["start"] <= 1.5 for s in segs) or (segs and segs[0].get("zoom", 1) != 1)
    hook = (5 if first_word <= 0.5 else 2 if first_word <= 1.0 else 0) + (3 if early_cut else 0) \
        + (2 if caps and caps[0]["start"] <= 1.0 else 0)
    items["hook"] = {"score": float(hook), "why": f"first words at {first_word:.2f}s, "
                                                  f"visual change in 1.5s: {bool(early_cut)}"}
    if edl.get("drop_at") is not None:  # a DJ clip's hook is the drop itself: does it land in 1.5 s?
        items["hook"] = {"score": _band(edl["drop_at"], 0, 1.5, soft=6),
                         "why": f"the drop first hits at {edl['drop_at']:.1f}s"}

    # each boundary counts once, whether it is a cut, a punch-in change or both
    changes = sum(1 for a, b in zip(segs, segs[1:])
                  if b["src_in"] != a["src_out"] or a.get("zoom") != b.get("zoom"))
    per10 = changes / dur * 10 if dur else 0
    items["pacing"] = {"score": _band(per10, *CUTS_PER_10S, soft=4), "why": f"{per10:.1f} changes/10s"}

    covered = sum(c["end"] - c["start"] for c in caps)
    speech = sum(s["src_out"] - s["src_in"] for s in segs) or 1
    items["captions"] = {"score": round(min(10, 10 * covered / speech / 0.85), 1),
                         "why": f"{covered / speech:.0%} of speech captioned"}

    lo, hi = PLATFORM_SWEET_SPOT[platform]
    items["length"] = {"score": _band(dur, lo, hi, soft=30), "why": f"{dur:.1f}s ({platform} {lo}-{hi}s)"}

    lufs = loudness(render) if render and render.exists() else None
    items["audio"] = {"score": _band(lufs, TARGET_LUFS - 1, TARGET_LUFS + 1, soft=8) if lufs is not None else None,
                      "why": f"{lufs} LUFS (target {TARGET_LUFS})" if lufs is not None else "no render"}

    text = " ".join(c["text"] for c in caps)
    items["comment_trigger"] = {"score": 10.0 if CTA.search(text) else 3.0,
                                "why": "question/CTA in captions" if CTA.search(text) else "no question or CTA"}

    words = len(text.split())
    wps = words / covered if covered else 0
    items["text_density"] = {"score": _band(wps, 1.5, 3.5, soft=2.5), "why": f"{wps:.1f} words/s on screen"}

    if edl.get("kind") == "dj-drop":  # no speech: what counts is a hook caption up at once
        early = bool(caps) and caps[0]["start"] <= 0.5
        items["captions"] = {"score": 10.0 if early else 0.0,
                             "why": f"hook caption from {caps[0]['start']:.1f}s" if caps else "no hook caption"}
        items["text_density"] = {"score": None, "why": "not a speech edit"}

    items["payoff_loop"] = {"score": None, "why": "needs the LLM judge (ending leads back to the start)"}
    scored = [v["score"] for v in items.values() if v["score"] is not None]
    return {"total": round(sum(scored) / len(scored), 1) if scored else None, "platform": platform,
            "items": items}
