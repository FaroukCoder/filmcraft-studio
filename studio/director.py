"""The creative director (master plan ④ planner + ⑨ judge) for DJ drop clips.

1. plan_dj: from the detected moments, pick the best ones and design 3 distinct variants of each
   (tease, length, hook text, drop graphic), all from menus the builder can execute, so even a
   small local model can't ask for something impossible. provider "rules" is the no-LLM plan.
2. contact_sheet: one image per moment, a row of key frames per variant, labelled.
3. judge: an LLM looks at the sheet plus each variant's measured rubric and QA, scores hook,
   payoff/loop and visual quality, and names one fix. rank() merges judge and rubric.
Every decision records which provider/model made it (llm.ask)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import llm
from .plan import STAMPS

N_VARIANTS = 3
VARIANT = {"type": "object", "required": ["name", "tease_bars", "before_bars", "after_bars", "hook_text", "stamp"],
           "properties": {"name": {"type": "string"},
                          "tease_bars": {"type": "integer", "enum": [0, 1, 2]},
                          "before_bars": {"type": "integer", "enum": [2, 4, 8]},
                          "after_bars": {"type": "integer", "enum": [4, 8, 16]},
                          "hook_text": {"type": "string"},
                          "stamp": {"type": "string", "enum": list(STAMPS)}}}
PLAN_SCHEMA = {"type": "object", "required": ["picks"], "properties": {"picks": {"type": "array", "items": {
    "type": "object", "required": ["moment", "why", "variants"],
    "properties": {"moment": {"type": "integer"}, "why": {"type": "string"},
                   "variants": {"type": "array", "items": VARIANT, "minItems": N_VARIANTS,
                                "maxItems": N_VARIANTS}}}}}}
JUDGE_SCHEMA = {"type": "object", "required": ["variants", "best"], "properties": {
    "best": {"type": "string"},
    "variants": {"type": "array", "items": {"type": "object", "required": ["name", "hook", "payoff_loop", "visual", "fix"],
                 "properties": {"name": {"type": "string"},
                                "hook": {"type": "integer", "minimum": 0, "maximum": 10},
                                "payoff_loop": {"type": "integer", "minimum": 0, "maximum": 10},
                                "visual": {"type": "integer", "minimum": 0, "maximum": 10},
                                "fix": {"type": "string"}}}}}}

PLAN_PROMPT = """You are the editor of a DJ's Instagram Reels. From a recorded techno set, choose the {n} best
drop moments and design {v} clearly different vertical clips of each.

What makes these clips work: the payoff must land within the first 1.5 s (a "tease" of 1-2 bars of
the drop at the start does this, then the clip cuts back to the build-up); the clip should loop
cleanly; 15-45 s total; one short caption on screen the whole time (max 5 words, uppercase, a
question or tease that makes people comment, e.g. "TRACK ID?", "WAIT FOR IT", "WHO MADE THIS?").
Bigger breakdowns (break_s) and higher score mean a harder-hitting drop. Prefer moments whose
tempo is "sure": an UNSURE tempo means the bar cuts may land off the beat.

Menus (pick from these only):
- tease_bars 0|1|2: bars of the drop shown first (0 = start straight on the build-up)
- before_bars 2|4|8: build-up before the drop; after_bars 4|8|16: payoff after it
- stamp: "track-id" (TRACK ID? slams in on the drop), "kinetic-title" (the caption words pop in on the
  drop), "none"
One bar here lasts {bar:.2f} s at the set's tempo.

Detected moments (index, drop time in the set, tempo, breakdown length, score):
{table}

Answer with JSON: picks = [{{moment: index, why, variants: [{v} variants with a short distinct name each]}}],
best moment first."""

JUDGE_PROMPT = """You are judging {v} versions of the same DJ Reel. The image shows one row per version (label on
the left); frames left to right are taken at the times written under them. Measured facts per version:
{facts}

Score each version 0-10 on: hook (does the first second grab: the drop or striking motion, readable
caption), payoff_loop (does it deliver and would it loop cleanly), visual (framing on the DJ, caption
legibility, graphics not covering the action). Give one concrete fix per version and name the best."""


def rules_plan(moments: list[dict], n: int) -> dict:
    """No-LLM plan: the top-scoring moments, three proven variants each."""
    variants = [{"name": "tease", "tease_bars": 1, "before_bars": 4, "after_bars": 8, "hook_text": "TRACK ID?", "stamp": "track-id"},
                {"name": "build-up", "tease_bars": 0, "before_bars": 4, "after_bars": 8, "hook_text": "WAIT FOR IT", "stamp": "kinetic-title"},
                {"name": "short-punch", "tease_bars": 2, "before_bars": 2, "after_bars": 8, "hook_text": "TRACK ID?", "stamp": "track-id"}]
    picks = sorted(range(len(moments)), key=lambda i: (not moments[i].get("bpm_sure", True), -moments[i]["score"]))[:n]
    return {"picks": [{"moment": i, "why": "highest drop score with a sure tempo", "variants": variants} for i in picks]}


def _clean(plan: dict, moments: list[dict], n: int) -> list[dict]:
    """Keep valid, distinct picks; tidy captions; exactly N_VARIANTS uniquely named variants."""
    out, seen = [], set()
    for p in plan["picks"]:
        if not (0 <= p["moment"] < len(moments)) or p["moment"] in seen or len(p["variants"]) < N_VARIANTS:
            continue
        seen.add(p["moment"])
        names = set()
        for k, v in enumerate(p["variants"][:N_VARIANTS]):
            v["hook_text"] = " ".join(v["hook_text"].upper().split()[:5])
            v["name"] = "".join(c if c.isalnum() else "-" for c in v["name"].lower()).strip("-")[:24] or f"v{k + 1}"
            if v["name"] in names:
                v["name"] += f"-{k + 1}"
            names.add(v["name"])
        out.append({**p, "variants": p["variants"][:N_VARIANTS]})
    return out[:n]


def plan_dj(moments: list[dict], n: int = 3, provider: str | None = None) -> dict:
    """{"picks": [...], "provider", "model"}; falls back to the rules plan if the LLM fails."""
    if not moments:
        return {"picks": [], "provider": "rules", "model": None}
    if (provider or llm.PROVIDER) == "rules":
        return {"picks": _clean(rules_plan(moments, n), moments, n), "provider": "rules", "model": None}
    bar = 4 * 60 / (sorted(m["bpm"] for m in moments)[len(moments) // 2])
    table = "\n".join(f"{i}: {int(m['at'] // 60)}:{m['at'] % 60:04.1f}, {m['bpm']} BPM "
                      f"({'sure' if m.get('bpm_sure', True) else 'UNSURE'}), break_s {m.get('break', 0)}, "
                      f"score {m['score']}" for i, m in enumerate(moments))
    try:
        r = llm.ask(PLAN_PROMPT.format(n=n, v=N_VARIANTS, bar=bar, table=table), PLAN_SCHEMA, provider=provider)
        picks = _clean(r["data"], moments, n)
        if picks:
            return {"picks": picks, "provider": r["provider"], "model": r["model"]}
        reason = "no valid picks"
    except (llm.LLMError, OSError, ValueError) as exc:
        reason = str(exc)[:200]
    return {"picks": _clean(rules_plan(moments, n), moments, n), "provider": "rules", "model": None,
            "fallback_reason": reason}


def frame_times(edl: dict) -> list[float]:
    """Key moments of a clip: the open, the first second, the drop, mid-payoff, the loop point."""
    d, drop = edl["duration"], edl["graphics"][0]["start"] if edl.get("graphics") else edl["drop_at"]
    return [round(t, 2) for t in (0.2, 1.0, min(drop + 0.3, d - 0.1), (drop + d) / 2, d - 0.3)]


def contact_sheet(rows: list[tuple[str, Path, list[float]]], out: Path, thumb_h: int = 320) -> Path:
    """rows = [(label, render, times)] -> one labelled grid image (row per variant)."""
    from PIL import Image, ImageDraw, ImageFont
    tw, label_w, foot = round(thumb_h * 9 / 16), 170, 26
    cols = max(len(t) for _, _, t in rows)
    sheet = Image.new("RGB", (label_w + cols * (tw + 6), len(rows) * (thumb_h + foot + 10)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    tmp = out.parent / f"{out.stem}_frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for r, (label, render, times) in enumerate(rows):
        y = r * (thumb_h + foot + 10)
        draw.text((10, y + thumb_h // 2 - 12), label[:14], fill=(255, 255, 255), font=font)
        for c, t in enumerate(times):
            f = tmp / f"{r}_{c}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(render), "-frames:v", "1",
                            "-vf", f"scale={tw}:{thumb_h}", str(f)], check=True)
            x = label_w + c * (tw + 6)
            sheet.paste(Image.open(f), (x, y))
            draw.text((x + 4, y + thumb_h + 2), f"{t:.1f}s", fill=(200, 200, 200), font=font)
    sheet.save(out)
    return out


PROMO_JUDGE_PROMPT = """You are judging {v} version(s) of a vertical motion-graphics video (Instagram Reel). The image
shows one row per version (label on the left); frames are taken mid-scene at the times under them.
Measured facts per version:
{facts}

Score each version 0-10 on: hook (does the first scene state something worth staying for, readable
in under 1.5 s), payoff_loop (does it build to a clear point and end on a call to action), visual
(type hierarchy, legibility on a phone, consistent alignment and spacing, nothing cramped or too
small, contrast). Give one concrete fix per version (name the scene) and name the best."""


def judge(sheet: Path, facts: dict[str, dict], provider: str | None = None, kind: str = "dj") -> dict:
    """facts = {variant name: {"seconds", "drop_at"?, "rubric", "qa"}} -> judge scores per variant.
    kind "dj" (drop clips) or "promo" (motion graphics) picks the judging brief."""
    lines = "\n".join(f"- {k}: {v['seconds']:.1f} s"
                      + (f", drop first hits at {v['drop_at']:.1f} s" if "drop_at" in v else "")
                      + f", measured rubric {v['rubric']}/10, QA {'clean' if not v['qa'] else '; '.join(v['qa'])}"
                      for k, v in facts.items())
    prompt = (PROMO_JUDGE_PROMPT if kind == "promo" else JUDGE_PROMPT).format(v=len(facts), facts=lines)
    r = llm.ask(prompt, JUDGE_SCHEMA, images=[sheet], provider=provider)
    by_name = {x["name"]: x for x in r["data"]["variants"] if x["name"] in facts}
    return {"scores": by_name, "best": r["data"]["best"], "provider": r["provider"], "model": r["model"]}


def rank(facts: dict[str, dict], verdict: dict | None) -> list[dict]:
    """Final order: half measured rubric, half the judge's mean; QA failures always go last."""
    out = []
    for name, f in facts.items():
        j = (verdict or {}).get("scores", {}).get(name)
        jm = round((j["hook"] + j["payoff_loop"] + j["visual"]) / 3, 2) if j else None
        total = round(f["rubric"] if jm is None else (f["rubric"] + jm) / 2, 2)
        out.append({"name": name, "total": total, "rubric": f["rubric"], "judge": jm,
                    "fix": j["fix"] if j else None, "qa_ok": not f["qa"]})
    return sorted(out, key=lambda x: (not x["qa_ok"], -x["total"]))
