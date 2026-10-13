"""Motion-graphics videos from a brief (master plan P4, general purpose: not tied to music).

    brief -> storyboard (LLM, or given) -> one HTML page (all scenes on one CSS timeline)
          -> frame-exact render (mograph.render, virtual clock) -> H.264 MP4 (+ optional music)

Storyboard: {"theme": {...}?, "scenes": [{"type", "duration", ...fields}]}, types:
  title {headline, sub?} · words {text} · list {title?, items[2-5]} · stat {value, prefix?, suffix?,
  label} · image {src, caption?} · cta {headline, handle?}
The look follows studio/direction (CLAUDE.md, system/never.md, system/motion.md) and a pack
(`house` = the owner's whatstheID identity): words rise whole out of masks on uneven onsets, the
camera never settles (every scene drifts and pushes in), scenes cut hard mid-motion, exits
accelerate, nothing fades in or bounces, no caps, no accent word, no bullet dots, no stat slide;
the pack's accent appears once (the handle). Layout keeps the 9:16 safe zones."""
from __future__ import annotations

import html as _html
import json
import subprocess
from pathlib import Path

from . import llm, mograph

W, H, FPS = 1080, 1920, 30
PACK = "house"
EXIT = 0.27  # seconds: every scene accelerates away over its last 8 frames, then hard-cuts
TYPES = ("title", "words", "list", "stat", "image", "cta")

CSS = """
@property --n { syntax: '<integer>'; initial-value: 0; inherits: false; }
html,body{margin:0;width:%(W)spx;height:%(H)spx;overflow:hidden;background:var(--ground,#04030a)}
.bg{position:absolute;inset:-6%%;background:var(--field,var(--ground));animation:push %(total)ss linear both}
.bg img{position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover;filter:brightness(.3) saturate(.75) blur(4px);
  mix-blend-mode:screen}
.scene{position:absolute;inset:0;opacity:0}
@keyframes on{from{opacity:1}to{opacity:1}}
.cam{position:absolute;inset:0}
.safe{position:absolute;left:8%%;right:8%%;top:14%%;bottom:24%%;display:flex;flex-direction:column;
  justify-content:center;align-items:center;text-align:center;gap:44px;color:var(--t-hi,#f2efff)}
.h{font:normal 400 116px/1.12 var(--name-font);letter-spacing:var(--name-track,0);margin:0}
.b{font:normal var(--body-weight,400) 56px/1.35 var(--body-font);color:var(--t-mid,#a89cd4);margin:0}
.mask{display:inline-block;overflow:hidden;vertical-align:top;padding:0 .05em .14em;margin-bottom:-.14em}
.mask>span{display:inline-block}
.line{display:block}
.num{counter-reset:n var(--n)}
.num .v::after{content:counter(n)}
.img{position:absolute;inset:0;overflow:hidden}
.img img{width:100%%;height:100%%;object-fit:cover}
.shade{position:absolute;inset:0;background:linear-gradient(transparent 45%%,rgba(4,3,10,.82) 80%%)}
.handle{font:normal 500 50px/1 var(--body-font);color:var(--accent)}
@keyframes up{from{transform:translateY(108%%)}to{transform:none}}
@keyframes drift{from{transform:none}to{transform:translateX(-6%%) scale(1.06)}}
@keyframes push{from{transform:none}to{transform:scale(1.18) translate3d(-3%%,2%%,0)}}
@keyframes leave{from{transform:none;filter:blur(0)}to{transform:translateY(-9%%) scale(.97);filter:blur(6px)}}
@keyframes kb{from{transform:scale(1.04)}to{transform:scale(1.16) translate3d(-2%%,-2%%,0)}}
"""


def _a(name: str, dur: float, delay: float, ease: str = "var(--ease-land)", fill: str = "both") -> str:
    return f"{name} {dur:.3f}s {ease} {delay:.3f}s {fill}"


def _esc(s) -> str:
    return _html.escape(str(s))


def _words(text: str, t0: float, first: int = 5, rest: int = 4) -> str:
    """Whole words rising out of their own masks, on uneven onsets (motion.md: 4-6 f in a headline)."""
    out, f = [], 0
    for i, w in enumerate(text.split()):
        out.append(f'<span class="mask"><span style="animation:{_a("up", 0.42, t0 + f / FPS)}">{_esc(w)}</span></span> ')
        f += first if i == 0 else rest
    return "".join(out)


def _scene(s: dict, t0: float) -> str:
    """One scene's HTML. t0 = its start on the global timeline (all delays are absolute)."""
    d, k = float(s["duration"]), s["type"]
    end = t0 + d
    leave = _a("leave", EXIT, end - EXIT, "var(--ease-leave)", "forwards")
    if k == "title":
        body = (f'<h1 class="h">{_words(s["headline"], t0)}</h1>'
                + (f'<p class="b">{_words(s["sub"], t0 + 0.5, 3, 2)}</p>' if s.get("sub") else ""))
    elif k == "words":
        body = f'<h1 class="h">{_words(s["text"], t0)}</h1>'
    elif k == "list":  # lines, no dots; the title is just the first line
        lines = ([s["title"]] if s.get("title") else []) + s["items"][:5]
        body = "".join(f'<p class="{"h" if i == 0 and s.get("title") else "b"} line" style="color:var(--t-hi)">'
                       f'{_words(x, t0 + 0.08 + i * 0.27, 3, 2)}</p>' for i, x in enumerate(lines))
    elif k == "stat":  # the number sits inside its sentence, stepping per frame, never a stat slide
        count = max(0.6, min(1.4, d * 0.4))
        key = f"count{int(t0 * 1000)}"
        body = (f'<style>@keyframes {key}{{from{{--n:0}}to{{--n:{int(s["value"])}}}}}</style>'
                f'<p class="h"><span class="mask"><span style="animation:{_a("up", 0.42, t0)}">'
                f'{_esc(s.get("prefix", ""))}<span class="num" style="animation:{_a(key, count, t0)}">'
                f'<span class="v"></span></span>{_esc(s.get("suffix", ""))}</span></span> '
                f'{_words(s["label"], t0 + 0.2)}</p>')
    elif k == "image":
        cap = (f'<div class="safe" style="justify-content:flex-end"><p class="h" style="font-size:76px">'
               f'{_words(s["caption"], t0 + 0.25)}</p></div>') if s.get("caption") else ""
        src = Path(s["src"]).resolve().as_uri()
        return (f'<section class="scene" style="animation:on {d:.3f}s linear {t0:.3f}s">'
                f'<div class="img"><img src="{src}" style="animation:kb {d:.3f}s linear {t0:.3f}s both"></div>'
                f'<div class="shade"></div><div class="cam" style="animation:{leave}">{cap}</div></section>')
    elif k == "cta":  # small, the handle once in the accent; it keeps drifting to the last frame
        body = (f'<h1 class="h" style="font-size:72px">{_words(s["headline"], t0)}</h1>'
                + (f'<div class="handle">{_words(s["handle"], t0 + 0.35)}</div>' if s.get("handle") else ""))
        leave = ""
    else:
        raise ValueError(f"unknown scene type {k!r} (one of {TYPES})")
    drift = f"animation:drift {d:.3f}s linear {t0:.3f}s both"
    inner = f"animation:{leave}" if leave else ""
    return (f'<section class="scene" style="animation:on {d:.3f}s linear {t0:.3f}s">'
            f'<div class="cam" style="{drift}"><div class="cam" style="{inner}">'
            f'<div class="safe">{body}</div></div></div></section>')


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
    return [...box.querySelectorAll('*:not(.mask)')].some(e => { const r = e.getBoundingClientRect();  // a mask's padding is room for descenders
      return r.width && (r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1); }); };
  document.querySelectorAll('.safe').forEach(box => {
    const els = [...box.querySelectorAll('.h,.b,.handle')];
    while (spills(box) && els.some(el => parseFloat(getComputedStyle(el).fontSize) > 36))
      els.forEach(el => { const fs = parseFloat(getComputedStyle(el).fontSize);
        if (fs > 36) el.style.fontSize = (fs * 0.95) + 'px'; });  // shrink together, keep the hierarchy
    if (spills(box)) bad.push(box.innerText.slice(0, 40));
  });
  off.remove();  // animations come back; the renderer seeks each from frame 0
  return bad; };
</script>"""


def compose(board: dict, pack: str = PACK) -> tuple[str, float]:
    """Storyboard -> (HTML page, total seconds)."""
    t, scenes = 0.0, []
    for s in board["scenes"]:
        scenes.append(_scene(s, t))
        t += float(s["duration"])
    css = mograph.pack_css(pack) + CSS % {"W": W, "H": H, "total": t}
    # the ground is a real surface when there is one: the footage itself, dark, under the brand field
    plate = f'<img src="{Path(board["plate"]).resolve().as_uri()}">' if board.get("plate") else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style>{FIT}</head>'
            f'<body><div class="bg">{plate}</div>{"".join(scenes)}</body></html>'), t


def render_video(board: dict, out: Path, music: Path | None = None, pack: str = PACK) -> dict:
    """Render the storyboard to `out` (H.264, yuv420p, 30 fps) through the pack's grade (grain);
    music bed trimmed, faded, -14 LUFS. The page is kept beside it (`<out>.html`) for lint.mjs."""
    page, total = compose(board, pack)
    out.with_suffix(".html").write_text(page, encoding="utf-8")
    frames_dir = out.parent / f"{out.stem}_frames"
    info: dict = {}
    frames = mograph.render(page, frames_dir, total, FPS, (W, H), prepare="window.__fit()", info=info, alpha=False)
    args = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f_%05d.jpg")]
    if music:
        args += ["-i", str(music), "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(0.0, total - 1.2):.2f}:d=1.2,"
                                          "loudnorm=I=-14:TP=-2:LRA=11", "-shortest", "-c:a", "aac", "-b:a", "192k"]
    if mograph.pack_grade(pack):
        args += ["-vf", mograph.pack_grade(pack)]
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

Rules (studio/direction/jobs/promo.md): open with the most interesting true thing in under 6 words
(the first 1.5 s decide if people keep watching); one idea per scene; plain verbs, sentence case or
lowercase, never all caps; max ~6 words per scene (list items max 5 words, 2-4 items). Be specific
("62 minutes in, 9 clips out"), not a slogan: never "Not just X. It's Y.", "No X. Just Y.", one-word
triplets, "unlock", "meet", "the future of", "elevate", "seamless". No em dashes. Prefer "words" and
"image" scenes; "stat" only for a number the brief states. End with a short "cta" (1.5-2.2 s).
Durations 1.5-6 s: about 0.3 s per word on screen plus 1 s. Scene types and their fields:
- title: headline, sub (optional, one short line)
- words: text (a statement, revealed word by word)
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
