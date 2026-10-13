"""Code motion graphics (master plan P4, Q5b): HTML/CSS animation -> transparent PNG frames ->
FilmCraft image sequence on a track above the footage (the HyperFrames idea, but stepped
frame by frame so the render is exact and repeatable).

Contract for any HTML (built-in templates, local-LLM or Claude-written): animate with CSS/WAAPI,
any requestAnimationFrame/timer-driven JS (GSAP, canvas, Three.js, Lottie: the virtual clock steps
it), paused GSAP timelines on `window.__timelines` (HyperFrames), or `window.seek(seconds)`; keep the
page background transparent. Rendered in the Edge that ships with Windows (no download)."""
from __future__ import annotations

import html as _html
import shutil
from pathlib import Path

ACCENT = "#FFD400"  # visual identity is fluid (Q13): style packs will override this

_BASE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:%(w)spx;height:%(h)spx;background:transparent;overflow:hidden;
  font-family:'Inter','Segoe UI',Arial,sans-serif}
%(css)s</style></head><body>%(body)s</body></html>"""

TEMPLATES = {
    # words pop in one by one, the last one in the accent colour
    "kinetic-title": {
        "css": """.t{position:absolute;left:0;right:0;top:%(y)s%%;text-align:center;font-weight:900;
  font-size:%(size)spx;line-height:1.05;color:#fff;text-transform:uppercase;
  text-shadow:0 6px 0 rgba(0,0,0,.55)}
.w{display:inline-block;margin:0 .12em;opacity:0;transform:scale(.3) translateY(40px);
  animation:pop .38s cubic-bezier(.2,1.6,.4,1) forwards}
.w:last-child{color:%(accent)s}
@keyframes pop{to{opacity:1;transform:scale(1) translateY(0)}}""",
        "body": lambda p: '<div class="t">' + "".join(
            f'<span class="w" style="animation-delay:{i * p["stagger"]:.2f}s">{_html.escape(w)}</span>'
            for i, w in enumerate(p["text"].split())) + "</div>",
        "defaults": {"y": 38, "size": 120, "stagger": 0.14},
    },
    # name + role on an accent bar that slides in, holds, slides out
    "lower-third": {
        "css": """.lt{position:absolute;left:60px;top:%(y)s%%;transform:translateX(-120%%);
  animation:in .5s cubic-bezier(.2,.9,.3,1) forwards, out .45s ease-in %(out)ss forwards}
.n{background:%(accent)s;color:#111;font-weight:900;font-size:64px;padding:14px 28px;display:inline-block}
.r{background:rgba(0,0,0,.78);color:#fff;font-size:40px;padding:10px 28px;display:inline-block;margin-top:6px}
@keyframes in{to{transform:translateX(0)}}
@keyframes out{to{transform:translateX(-120%%)}}""",
        "body": lambda p: f'<div class="lt"><div class="n">{_html.escape(p["text"])}</div><br>'
                          f'<div class="r">{_html.escape(p.get("sub", ""))}</div></div>',
        "defaults": {"y": 66, "out": 2.6},
    },
    # "TRACK ID?" stamp: slams in with a shake, accent underline sweeps across
    "track-id": {
        "css": """.s{position:absolute;left:0;right:0;top:%(y)s%%;text-align:center;font-weight:900;
  font-size:%(size)spx;color:#fff;letter-spacing:.04em;text-shadow:0 0 28px rgba(0,0,0,.6);
  transform:scale(2.4);opacity:0;animation:slam .28s cubic-bezier(.2,1.4,.4,1) forwards,
  shake .5s linear .28s 1}
.u{position:absolute;left:50%%;top:calc(%(y)s%% + %(size)spx * 1.25);height:14px;width:0;
  transform:translateX(-50%%);background:%(accent)s;animation:sweep .45s ease-out .3s forwards}
@keyframes slam{to{transform:scale(1);opacity:1}}
@keyframes shake{20%%{transform:translate(-8px,4px)}40%%{transform:translate(7px,-5px)}
  60%%{transform:translate(-5px,3px)}80%%{transform:translate(4px,-2px)}100%%{transform:none}}
@keyframes sweep{to{width:62%%}}""",
        "body": lambda p: f'<div class="s">{_html.escape(p["text"])}</div><div class="u"></div>',
        "defaults": {"y": 16, "size": 130},
    },
}


def template_html(name: str, size: tuple[int, int] = (1080, 1920), accent: str = ACCENT, **params) -> str:
    t = TEMPLATES[name]
    p = {**t["defaults"], **params, "accent": accent}
    return _BASE % {"w": size[0], "h": size[1], "css": t["css"] % p, "body": t["body"](p)}


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
           size: tuple[int, int] = (1080, 1920)) -> list[Path]:
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
        page.goto(page_file.as_uri())
        page.evaluate("document.fonts.ready")
        for i in range(round(duration * fps)):
            page.evaluate(_STEP, i / fps)
            f = out_dir / f"f_{i:05d}.png"
            page.screenshot(path=str(f), omit_background=True)
            frames.append(f)
        browser.close()
    return frames


def place(fc, frames_dir: Path, start: float, track: str = "V2") -> dict:
    """Import a rendered PNG sequence into an open FilmCraft session and put it on `track`."""
    from .fc import ticks
    first = sorted(frames_dir.glob("f_*.png"))[0]
    item = fc.run("file.importImageSequence", path=str(first))["items"][0]
    return fc.run("timeline.place", item=item, track=track, time=ticks(start), audio=False)
