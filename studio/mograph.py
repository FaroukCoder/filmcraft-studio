"""Code motion graphics (master plan P4, Q5b): HTML/CSS animation -> transparent PNG frames ->
FilmCraft image sequence on a track above the footage (the HyperFrames idea, but stepped
frame by frame so the render is exact and repeatable).

Contract for any HTML (built-in templates, local-LLM or Claude-written): animate with CSS/WAAPI,
any requestAnimationFrame/timer-driven JS (GSAP, canvas, Three.js, Lottie: the virtual clock steps
it), paused GSAP timelines on `window.__timelines` (HyperFrames), or `window.seek(seconds)`; keep the
page background transparent. Rendered in the Edge that ships with Windows (no download)."""
from __future__ import annotations

import html as _html
import re
import shutil
from pathlib import Path

# Looks come from the direction folder (studio/direction/CLAUDE.md): packs/<name>.css holds the
# fonts, colours, curves and footage grade; system/never.md and motion.md are the rules these
# templates follow (words land whole out of masks, arrivals decelerate from oversize, exits
# accelerate, nothing fades in, no caps, no accent word, no bounce).
DIRECTION = Path(__file__).parent / "direction"
PACK = "club"  # DJ clients' default; the owner's own channel uses "house"


def pack_css(name: str = PACK) -> str:
    """The pack's CSS with its font URLs made absolute (pages render from a temp folder)."""
    css = (DIRECTION / "packs" / f"{name}.css").read_text(encoding="utf-8")
    return css.replace("url(fonts/", "url(" + (DIRECTION / "fonts").as_uri() + "/")


def pack_grade(name: str = PACK) -> str | None:
    """The pack's ffmpeg footage grade (`--grade: "..."`), or None."""
    m = re.search(r'--grade:\s*"([^"]+)"', pack_css(name))
    return m[1] if m else None


_BASE = """<!doctype html><html><head><meta charset="utf-8"><style>%(pack)s
html,body{margin:0;width:%(w)spx;height:%(h)spx;background:transparent;overflow:hidden;
  font-family:var(--body-font);color:var(--ink,var(--t-hi))}
.mask{display:inline-block;overflow:hidden;vertical-align:top;padding:0 .04em .12em}
.mask>span{display:inline-block}
%(css)s</style></head><body>%(body)s
<script>/* fit: a line never wider than its box (layout is time-independent, so frames stay exact) */
document.fonts.ready.then(() => document.querySelectorAll('[data-fit]').forEach(el => {
  const max = el.parentElement.clientWidth * +el.dataset.fit; let fs = parseFloat(getComputedStyle(el).fontSize);
  while (el.scrollWidth > max && fs > 24) { fs *= .96; el.style.fontSize = fs + 'px'; } }));</script>
</body></html>"""


def _gaps(n: int, first: int = 3, rest: int = 2) -> list[int]:
    """Uneven word onsets in frames (3,2,2,2...: motion.md), cumulative."""
    out, f = [], 0
    for i in range(n):
        out.append(f)
        f += first if i == 0 else rest
    return out


def _risen(words: list[str], fps: int, at: float, gaps: list[int], cls: str = "") -> str:
    """Each word rises out of its own mask, landing on the ease-land curve."""
    return "".join(f'<span class="mask"><span class="rise {cls}" style="animation-delay:{at + g / fps:.3f}s">'
                   f'{_html.escape(w)}</span></span> ' for w, g in zip(words, gaps))


TEMPLATES = {
    # the DJ's name lands once on the drop: from 2.2x oversize and blurred, decelerating (60-72 %
    # of the travel in the first 5 frames), keeps shrinking while it holds, then leaves upward fast
    "name": {
        "css": """.nm{position:absolute;left:8%%;right:8%%;top:%(y)s%%;text-align:center}
.nm b{display:inline-block;font:normal var(--name-weight,400) %(size)spx/1 var(--name-font);
  font-stretch:var(--name-stretch,100%%);letter-spacing:var(--name-track,0);white-space:nowrap;
  text-shadow:0 2px 16px var(--shade,rgba(4,3,10,.6)),0 0 48px var(--shade,rgba(4,3,10,.6));
  animation:land .5s var(--ease-land) both, hold %(hold)ss linear .5s forwards, go .3s var(--ease-leave) %(out)ss forwards}
@keyframes land{from{transform:scale(2.2);filter:blur(10px)}to{transform:scale(1);filter:blur(0)}}
@keyframes hold{from{transform:scale(1)}to{transform:scale(.965) translateX(-1.2%%)}}
@keyframes go{from{transform:scale(.965) translateX(-1.2%%);opacity:1}to{transform:scale(.9) translate(-1.2%%,-40%%);opacity:0}}""",
        "body": lambda p: f'<div class="nm"><b data-fit=".9">{_html.escape(p["text"].lower())}</b></div>',
        "defaults": {"y": 17, "size": 150, "out": 2.2},
    },
    # a real track credit, lower left, clear of the decks: title then artist rise out of masks,
    # hold with a slow drift, then drop back into their masks (faster than they came)
    "credit": {
        "css": """.cr{position:absolute;left:7.5%%;right:16%%;top:%(y)s%%;font-family:var(--body-font);
  font-weight:var(--body-weight,400);font-stretch:var(--body-stretch,100%%);text-shadow:0 0 28px var(--shade,rgba(4,3,10,.6));
  animation:drift %(out)ss linear both}
.cr .t{font-size:%(size)spx;line-height:1.1}
.cr .a{font-size:calc(%(size)spx * .74);color:var(--ink-dim,var(--t-mid));line-height:1.2}
.rise{animation:up .42s var(--ease-land) both, down .24s var(--ease-leave) %(out)ss forwards}
@keyframes up{from{transform:translateY(105%%)}to{transform:none}}
@keyframes down{from{transform:none}to{transform:translateY(105%%)}}
@keyframes drift{from{transform:none}to{transform:translateX(1.5%%)}}""",
        "body": lambda p: (f'<div class="cr"><div class="t">{_risen([p["text"]], 30, 0.0, [0])}</div>'
                           + (f'<div class="a">{_risen([p["sub"]], 30, 0.0, [4])}</div>' if p.get("sub") else "")
                           + "</div>"),
        "defaults": {"y": 64, "size": 64, "out": 3.4},
    },
    # a short statement, word by word out of masks on uneven onsets, sentence case, one colour
    "kinetic-title": {
        "css": """.kt{position:absolute;left:8%%;right:8%%;top:%(y)s%%;text-align:center;
  font:normal 400 %(size)spx/1.08 var(--name-font);font-stretch:var(--name-stretch,100%%);
  letter-spacing:var(--name-track,0);text-shadow:0 0 36px var(--shade,rgba(4,3,10,.6));
  animation:drift %(out)ss linear both}
.rise{animation:up .42s var(--ease-land) both, down .24s var(--ease-leave) %(out)ss forwards}
@keyframes up{from{transform:translateY(105%%)}to{transform:none}}
@keyframes down{from{transform:none}to{transform:translateY(-105%%)}}
@keyframes drift{from{transform:none}to{transform:translateX(-2%%)}}""",
        "body": lambda p: f'<div class="kt">{_risen(p["text"].split(), 30, 0.0, _gaps(len(p["text"].split())))}</div>',
        "defaults": {"y": 38, "size": 96, "out": 2.4},
    },
}


def template_html(name: str, size: tuple[int, int] = (1080, 1920), pack: str = PACK, **params) -> str:
    t = TEMPLATES[name]
    p = {**t["defaults"], **params}
    p.setdefault("hold", max(0.1, p["out"] - 0.5))
    return _BASE % {"w": size[0], "h": size[1], "pack": pack_css(pack), "css": t["css"] % p, "body": t["body"](p)}


# Virtual clock, injected before the page's own scripts (the timeweb/timecut and Replit-renderer
# technique): Date, performance.now, rAF and timers run on a timeline that only moves when we step
# a frame, so canvas/GSAP/Three.js/Lottie animations land exactly on each frame however slow the
# screenshot is. Worker-thread canvases would bypass it, so OffscreenCanvas is switched off.
_CLOCK = """(() => {
  let now = 0, timers = [], rafs = [], nextId = 1;
  const RealDate = Date, t0 = RealDate.now();
  performance.now = () => now;
  window.Date = class extends RealDate {
    constructor(...a) { super(...(a.length ? a : [t0 + now])); }
    static now() { return t0 + now; }
  };
  const add = (fn, ms, args, every) => {
    const id = nextId++, step = Math.max(1, +ms || 0);  // >= 1 ms: a 0 ms chain can't spin forever
    timers.push({id, due: now + step, every: every ? step : 0, fn, args});
    return id;
  };
  window.setTimeout = (fn, ms, ...args) => add(fn, ms, args, false);
  window.setInterval = (fn, ms, ...args) => add(fn, ms, args, true);
  window.clearTimeout = window.clearInterval = id => { timers = timers.filter(t => t.id !== id); };
  window.requestAnimationFrame = fn => { const id = nextId++; rafs.push({id, fn}); return id; };
  window.cancelAnimationFrame = id => { rafs = rafs.filter(r => r.id !== id); };
  window.OffscreenCanvas = undefined;
  HTMLCanvasElement.prototype.transferControlToOffscreen = undefined;
  window.__vclock = {
    advance(to) {  // fire due timers in order, then one animation frame at `to` (ms)
      for (let t; (t = timers.sort((a, b) => a.due - b.due || a.id - b.id)[0]) && t.due <= to;) {
        now = t.due;
        if (t.every) t.due += t.every; else timers.shift();
        try { typeof t.fn === "function" ? t.fn(...t.args) : (0, eval)(t.fn); } catch (e) { console.error(e); }
      }
      now = to;
      const run = rafs; rafs = [];
      run.forEach(r => { try { r.fn(now); } catch (e) { console.error(e); } });
    }
  };
})();"""

# One frame: move the clock, seek CSS/WAAPI animations (each from when it first appeared, so one a
# script adds at 0.5 s starts at its own 0), seek HyperFrames-style paused GSAP timelines
# (`window.__timelines`, an object or array) and call an optional `window.seek(t)`.
_STEP = """t => {
  window.__vclock.advance(t * 1000);
  document.getAnimations().forEach(a => {
    if (a.__born === undefined) a.__born = t;
    a.pause(); a.currentTime = (t - a.__born) * 1000;
  });
  Object.values(window.__timelines || {}).forEach(tl => tl.seek ? tl.seek(t, false) : tl.time && tl.time(t));
  if (window.seek) window.seek(t);
}"""


def render(html: str, out_dir: Path, duration: float, fps: int = 30,
           size: tuple[int, int] = (1080, 1920), prepare: str | None = None,
           info: dict | None = None, alpha: bool = True) -> list[Path]:
    """Step the page frame by frame on a virtual clock and screenshot each frame with alpha."""
    import tempfile
    from playwright.sync_api import sync_playwright
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    frames = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_file = Path(tmp) / "graphic.html"  # a real navigation, so the clock script runs first
        page_file.write_text(html, encoding="utf-8")
        browser = pw.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.add_init_script(_CLOCK)
        page.goto(page_file.as_uri())  # waits for the load event, so images are in
        page.evaluate("document.fonts.ready")
        if prepare:  # one-off layout work before frame 0 (e.g. fitting text); its result -> info
            result = page.evaluate(prepare)
            if info is not None:
                info["prepare"] = result
        for i in range(round(duration * fps)):
            page.evaluate(_STEP, i / fps)
            if alpha:  # overlays need transparency: PNG
                f = out_dir / f"f_{i:05d}.png"
                page.screenshot(path=str(f), omit_background=True)
            else:  # opaque full-frame videos: JPEG q95 is ~2x faster to capture than PNG
                f = out_dir / f"f_{i:05d}.jpg"
                page.screenshot(path=str(f), type="jpeg", quality=95)
            frames.append(f)
        browser.close()
    return frames


def place(fc, frames_dir: Path, start: float, track: str = "V2") -> dict:
    """Import a rendered PNG sequence into an open FilmCraft session and put it on `track`."""
    from .fc import ticks
    first = sorted(frames_dir.glob("f_*.png"))[0]
    item = fc.run("file.importImageSequence", path=str(first))["items"][0]
    return fc.run("timeline.place", item=item, track=track, time=ticks(start), audio=False)
