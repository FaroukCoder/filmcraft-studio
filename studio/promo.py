"""Motion-graphics videos from a brief (master plan P4, general purpose: not tied to music).

    brief -> storyboard (LLM, or given) -> one HTML page (all scenes on one CSS timeline)
          -> frame-exact render (mograph.render, virtual clock) -> H.264 MP4 (+ optional music)

Storyboard: {"theme": {...}?, "scenes": [{"type", "duration", ...fields}]}, types:
  title {headline, sub?} · words {text} · list {title?, items[2-5]} · stat {value, prefix?, suffix?,
  label} · image {src, caption?} · cta {headline, handle?}
Motion follows the animate skill: CSS animations on transform/opacity/clip-path only, strong
ease-out for entrances (0.23,1,0.32,1), strong ease-in-out for on-screen moves (0.77,0,0.175,1),
linear only for Ken Burns drift; nothing scales from 0 (0.95 + fade); entrances stagger; exits
mirror the entrance, faster. Layout keeps 9:16 safe zones (Reels UI covers the bottom ~20%)."""
from __future__ import annotations

import html as _html
import json
import subprocess
from pathlib import Path

from . import llm, mograph

W, H, FPS = 1080, 1920, 30
EASE_OUT, EASE_IN_OUT = "cubic-bezier(0.23,1,0.32,1)", "cubic-bezier(0.77,0,0.175,1)"
THEME = {"bg": "#0b0b10", "bg2": "#1a1730", "fg": "#f5f5f7", "muted": "#a1a1b5", "accent": "#ffd400",
         "font": "'Segoe UI Black','Arial Black','Segoe UI',Arial,sans-serif",
         "body": "'Segoe UI Semibold','Segoe UI',Arial,sans-serif"}
EXIT = 0.35  # seconds: every scene leaves in the last EXIT s
TYPES = ("title", "words", "list", "stat", "image", "cta")

CSS = """
@property --n { syntax: '<integer>'; initial-value: 0; inherits: false; }
html,body{margin:0;width:%(W)spx;height:%(H)spx;overflow:hidden;background:%(bg)s}
.bg{position:absolute;inset:-10%%;background:radial-gradient(60%% 45%% at 30%% 25%%,%(bg2)s,transparent 70%%),
  %(bg)s;
  animation:drift %(total)ss linear both}
@keyframes drift{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(-3%%,2%%,0) scale(1.06)}}
.scene{position:absolute;inset:0;opacity:0}
@keyframes on{from{opacity:1}to{opacity:1}}
.safe{position:absolute;left:7%%;right:7%%;top:13%%;bottom:22%%;display:flex;flex-direction:column;
  justify-content:center;gap:40px;color:%(fg)s}
.h{font-family:%(font)s;font-size:150px;line-height:.98;letter-spacing:-.02em;text-transform:uppercase;margin:0}
.b{font-family:%(body)s;font-size:58px;line-height:1.25;color:%(muted)s;margin:0}
.acc{color:%(accent)s}
.w{display:inline-block;margin-right:.22em;vertical-align:top}  /* top: no baseline strut below the last line */
.bar{width:140px;height:14px;background:%(accent)s;transform-origin:left center}
.item{display:flex;gap:30px;align-items:baseline;font-family:%(body)s;font-size:78px;line-height:1.15}
.dot{flex:none;width:22px;height:22px;border-radius:50%%;background:%(accent)s;transform:translateY(-8px)}
.num{font-family:%(font)s;font-size:300px;line-height:.9;color:%(accent)s;letter-spacing:-.04em;
  counter-reset:n var(--n)}
.num .v::after{content:counter(n)}
.unit{font-size:.3em;letter-spacing:0;margin-left:.15em}
.img{position:absolute;inset:0;overflow:hidden}
.img img{width:100%%;height:100%%;object-fit:cover}
.shade{position:absolute;inset:0;background:linear-gradient(transparent 45%%,%(bg)sdd 85%%)}
.handle{font-family:%(body)s;font-size:54px;color:%(accent)s}
/* entrance and exit vocabulary (keyframes only touch transform / opacity / clip-path) */
@keyframes rise{from{opacity:0;transform:translateY(60px) scale(.95)}to{opacity:1;transform:none}}
@keyframes wipe{from{clip-path:inset(0 100%% 0 0)}to{clip-path:inset(0 0 0 0)}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes leave{from{opacity:1;transform:none}to{opacity:0;transform:translateY(-40px)}}
@keyframes kb{from{transform:scale(1.04) translate3d(0,0,0)}to{transform:scale(1.16) translate3d(-2%%,-2%%,0)}}
"""


def _a(name: str, dur: float, delay: float, ease: str = EASE_OUT) -> str:
    return f"{name} {dur:.3f}s {ease} {delay:.3f}s both"


def _esc(s) -> str:
    return _html.escape(str(s))


def _unit(suffix: str) -> str:
    """'%', 'x', 'k' sit at full size beside the number; a word ('variants') drops to a unit size."""
    return _esc(suffix) if len(suffix.strip()) <= 2 else f'<span class="unit">{_esc(suffix.strip())}</span>'


def _words(text: str, t0: float, step: float = 0.09, accent_last: bool = True) -> str:
    ws = text.split()
    return "".join(f'<span class="w{" acc" if accent_last and i == len(ws) - 1 and len(ws) > 1 else ""}" '
                   f'style="animation:{_a("rise", 0.6, t0 + i * step)}">{_esc(w)}</span>' for i, w in enumerate(ws))


def _scene(s: dict, t0: float) -> str:
    """One scene's HTML. t0 = its start on the global timeline (all delays are absolute)."""
    d, k = float(s["duration"]), s["type"]
    end = t0 + d
    leave = f"animation:{_a('leave', EXIT, end - EXIT, EASE_IN_OUT)}"
    if k == "title":
        body = (f'<div class="bar" style="animation:{_a("grow", 0.5, t0)}"></div>'
                f'<h1 class="h">{_words(s["headline"], t0 + 0.12)}</h1>'
                + (f'<p class="b" style="animation:{_a("rise", 0.6, t0 + 0.5)}">{_esc(s["sub"])}</p>' if s.get("sub") else ""))
    elif k == "words":
        body = f'<h1 class="h" style="font-size:120px">{_words(s["text"], t0, step=0.14)}</h1>'
    elif k == "list":
        items = s["items"][:5]
        body = ((f'<p class="b" style="animation:{_a("rise", 0.5, t0)}">{_esc(s["title"])}</p>' if s.get("title") else "")
                + "".join(f'<div class="item" style="animation:{_a("rise", 0.55, t0 + 0.25 + i * 0.32)}">'
                          f'<span class="dot"></span><span>{_esc(it)}</span></div>' for i, it in enumerate(items)))
    elif k == "stat":
        count = max(0.6, min(1.6, d * 0.45))  # count up with the entrance curve, then let it sit
        key = f"count{int(t0 * 1000)}"  # each stat counts to its own value
        body = (f'<style>@keyframes {key}{{from{{--n:0}}to{{--n:{int(s["value"])}}}}}</style>'
                f'<div class="num" style="animation:{_a("rise", 0.5, t0)},{_a(key, count, t0)}">'
                f'{_esc(s.get("prefix", ""))}<span class="v"></span>{_unit(s.get("suffix", ""))}</div>'
                f'<p class="b" style="font-size:64px;color:inherit;animation:{_a("rise", 0.6, t0 + 0.35)}">'
                f'{_esc(s["label"])}</p>')
    elif k == "image":
        cap = (f'<div class="safe" style="justify-content:flex-end"><p class="h" style="font-size:96px">'
               f'{_words(s["caption"], t0 + 0.3)}</p></div>') if s.get("caption") else ""
        src = Path(s["src"]).resolve().as_uri()
        return (f'<section class="scene" style="animation:on {d:.3f}s linear {t0:.3f}s">'
                f'<div class="img" style="animation:{_a("fade", 0.5, t0)}"><img src="{src}" '
                f'style="animation:kb {d:.3f}s linear {t0:.3f}s both"></div><div class="shade"></div>'
                f'<div style="{leave};position:absolute;inset:0">{cap}</div></section>')
    elif k == "cta":
        body = (f'<h1 class="h" style="font-size:130px">{_words(s["headline"], t0)}</h1>'
                + (f'<div class="handle" style="animation:{_a("wipe", 0.6, t0 + 0.5)}">{_esc(s["handle"])}</div>'
                   if s.get("handle") else ""))
        leave = ""  # the last word holds: a video ends on its call to action
    else:
        raise ValueError(f"unknown scene type {k!r} (one of {TYPES})")
    return (f'<section class="scene" style="animation:on {d:.3f}s linear {t0:.3f}s">'
            f'<div class="safe" style="{leave}">{body}</div></section>')


# Shrink any headline that overflows its box (measured once after fonts load, before frame 0;
# layout doesn't depend on time, so the render stays exact). Overflow left after that is reported.
FIT = """<script>
window.__fit = () => { const bad = [];
  // measure the resting layout: entrance poses (translateY) would count as overflow
  const off = document.createElement('style');
  off.textContent = '*{animation:none!important}';
  document.head.appendChild(off);
  // overflow = any element's layout box outside the safe box (not scrollHeight: with a tight
  // line-height the glyph ink pokes past the line box by design and would always "overflow")
  const spills = box => { const b = box.getBoundingClientRect();
    return [...box.querySelectorAll('*')].some(e => { const r = e.getBoundingClientRect();
      return r.width && (r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1); }); };
  document.querySelectorAll('.safe').forEach(box => {
    const els = [...box.querySelectorAll('.h,.item,.b,.num')];
    while (spills(box) && els.some(el => parseFloat(getComputedStyle(el).fontSize) > 36))
      els.forEach(el => { const fs = parseFloat(getComputedStyle(el).fontSize);
        if (fs > 36) el.style.fontSize = (fs * 0.95) + 'px'; });  // shrink together, keep the hierarchy
    if (spills(box)) bad.push(box.innerText.slice(0, 40));
  });
  off.remove();  // animations come back; the renderer seeks each from frame 0
  return bad; };
</script>"""


def compose(board: dict) -> tuple[str, float]:
    """Storyboard -> (HTML page, total seconds)."""
    theme = {**THEME, **board.get("theme", {})}
    t, scenes = 0.0, []
    for s in board["scenes"]:
        scenes.append(_scene(s, t))
        t += float(s["duration"])
    css = CSS % {"W": W, "H": H, "total": t, **theme}
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style>{FIT}</head>'
            f'<body><div class="bg"></div>{"".join(scenes)}</body></html>'), t


def render_video(board: dict, out: Path, music: Path | None = None) -> dict:
    """Render the storyboard to `out` (H.264, yuv420p, 30 fps); music bed trimmed, faded, -14 LUFS."""
    page, total = compose(board)
    frames_dir = out.parent / f"{out.stem}_frames"
    info: dict = {}
    frames = mograph.render(page, frames_dir, total, FPS, (W, H), prepare="window.__fit()", info=info, alpha=False)
    args = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f_%05d.jpg")]
    if music:
        args += ["-i", str(music), "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(0.0, total - 1.2):.2f}:d=1.2,"
                                          "loudnorm=I=-14:TP=-2:LRA=11", "-shortest", "-c:a", "aac", "-b:a", "192k"]
    args += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-t", f"{total:.3f}", str(out)]
    subprocess.run(args, check=True)
    return {"render": str(out), "seconds": round(total, 3), "frames": len(frames),
            "overflow": info.get("prepare") or []}


STORY_SCHEMA = {"type": "object", "required": ["scenes"], "properties": {"scenes": {"type": "array", "minItems": 3, "maxItems": 8,
    "items": {"type": "object", "required": ["type", "duration"], "properties": {
        "type": {"type": "string", "enum": list(TYPES)}, "duration": {"type": "number", "minimum": 1.5, "maximum": 6},
        "headline": {"type": "string"}, "sub": {"type": "string"}, "text": {"type": "string"},
        "title": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}},
        "value": {"type": "integer"}, "prefix": {"type": "string"}, "suffix": {"type": "string"},
        "label": {"type": "string"}, "caption": {"type": "string"}, "handle": {"type": "string"}}}}}}

STORY_PROMPT = """Write the storyboard for a vertical motion-graphics video (Instagram Reel, 9:16), {seconds} s total.
Brief: {brief}

Rules: open with a hook scene that states the most interesting point in under 6 words (the first
1.5 s decide if people keep watching); one idea per scene; short punchy words (headlines max 7
words, list items max 5 words, 2-4 items); end with a "cta" scene. Durations 1.5-6 s: about 0.3 s per
word on screen plus 1 s. Scene types and their fields:
- title: headline, sub (optional, one short line)
- words: text (a punchy statement, revealed word by word)
- list: title (optional), items
- stat: value (integer), prefix/suffix (optional, e.g. "$", "%", "x"), label
- cta: headline, handle (optional, e.g. "@name")
Use only facts from the brief; never invent numbers."""


def _clean_board(board: dict) -> dict:
    need = {"title": ["headline"], "words": ["text"], "list": ["items"], "stat": ["value", "label"],
            "image": ["src"], "cta": ["headline"]}
    scenes = [s for s in board["scenes"] if s.get("type") in need and all(s.get(f) not in (None, "", []) for f in need[s["type"]])]
    for s in scenes:
        s["duration"] = round(min(6.0, max(1.5, float(s["duration"]))), 2)
    if not scenes:
        raise ValueError("storyboard has no usable scenes")
    return {**board, "scenes": scenes}


def plan_storyboard(brief: str, seconds: int = 20, provider: str | None = None) -> dict:
    r = llm.ask(STORY_PROMPT.format(brief=brief, seconds=seconds), STORY_SCHEMA, provider=provider)
    return {**_clean_board(r["data"]), "provider": r["provider"], "model": r["model"]}


def contact_times(board: dict) -> list[float]:
    """Mid-point of every scene (after its entrance settles, before its exit)."""
    t, out = 0.0, []
    for s in board["scenes"]:
        out.append(round(t + min(float(s["duration"]) - EXIT - 0.05, 1.1), 2))
        t += float(s["duration"])
    return out


if __name__ == "__main__":
    import sys
    board = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(render_video(_clean_board(board), Path(sys.argv[2])), indent=1))
