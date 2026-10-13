"""Renderer checks in real Edge: python -m studio.test_mograph
1. A canvas ball driven by requestAnimationFrame + performance.now lands exactly where its own
   clock says on every frame (the virtual clock), and two renders are byte-identical.
2. A CSS template still steps: the TRACK ID stamp is invisible at 0 s and fully in at 0.5 s."""
import hashlib
import tempfile
from pathlib import Path

from PIL import Image

from studio import mograph

BALL = """<!doctype html><html><body style="margin:0;background:transparent">
<canvas id="c" width="600" height="100"></canvas><script>
const c = document.getElementById('c').getContext('2d'), t0 = performance.now();
(function draw() { const t = (performance.now() - t0) / 1000; c.clearRect(0, 0, 600, 100);
  c.fillStyle = '#f00'; c.beginPath(); c.arc(50 + 300 * t, 50, 10, 0, 7); c.fill();
  requestAnimationFrame(draw); })();
</script></body></html>"""


def red_x(p: Path, y: int) -> float | None:
    im = Image.open(p).convert("RGBA")
    px = im.load()
    xs = [x for x in range(im.width) if px[x, y][3] > 128 and px[x, y][0] > 200]
    return (min(xs) + max(xs)) / 2 if xs else None


with tempfile.TemporaryDirectory() as tmp:
    runs = []
    for n in range(2):
        frames = mograph.render(BALL, Path(tmp) / f"ball{n}", duration=1.0, fps=30, size=(600, 100))
        for i in (0, 15, 29):
            x = red_x(frames[i], 50)
            assert x is not None and abs(x - (50 + 300 * i / 30)) <= 1.5, (i, x)
        runs.append(hashlib.md5(b"".join(f.read_bytes() for f in frames)).hexdigest())
    assert runs[0] == runs[1], "renders differ between runs"

    stamp = mograph.render(mograph.template_html("track-id", (540, 960), text="ID?"), Path(tmp) / "stamp",
                           duration=0.6, fps=10, size=(540, 960))
    alpha = lambda p: Image.open(p).convert("RGBA").getchannel("A").getextrema()[1]  # noqa: E731
    assert alpha(stamp[0]) == 0 and alpha(stamp[5]) == 255
print("ok")
