"""Checks beat_lint.py on a small HyperFrames-style composition at 150 BPM (beat 0.4 s, bar
1.6 s, first downbeat 0.1 s): on-beat clips pass, off-beat ones are reported with how far off,
a title marked data-beat="bar" must sit on a bar line, relative starts are resolved, an
opt-out is honoured, and the two GSAP tells (an in-out slide, typed-out text) are found
while an out-eased move is not; a tween positioned between beats is reported.

    python test_beat_lint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import beat_lint  # noqa: E402

HTML = """<!doctype html>
<html data-start="0" data-duration="16">
<body>
  <section id="intro" data-start="0.1" data-duration="1.6" data-track-index="1"></section>
  <section id="title" data-beat="bar" data-start="1.7" data-duration="3.2" data-track-index="2"></section>
  <section id="late" data-start="2.25" data-duration="0.8" data-track-index="3"></section>
  <section id="after" data-start="intro + 0.4" data-duration="0.4" data-track-index="4"></section>
  <section id="loose" data-beat="off" data-start="3.333" data-duration="1" data-track-index="5"></section>
  <section id="barmiss" data-beat="bar" data-start="2.5" data-duration="1.6" data-track-index="6"></section>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.to(document.querySelector("#title"), { x: 240, duration: 0.8, ease: "power2.inOut" }, 1.7);
    tl.to("#intro", { yPercent: -100, duration: 0.4, ease: "expo.out" }, 0.1);
    tl.from(".headline", { text: "", duration: 1.2 }, 2.1);
    tl.to(".tag", { opacity: 1, duration: 0.2 }, 1.95);
  </script>
</body>
</html>"""


def main() -> int:
    problems = []
    findings = beat_lint.lint(HTML, bpm=150, downbeat=0.1, fps=30)
    codes = [(f["code"], f.get("clip")) for f in findings]
    want_present = [("off_beat", "late"), ("off_bar", "barmiss"), ("eased_slide", None), ("typewriter_text", None),
                    ("tween_off_beat", None)]
    for w in want_present:
        if w not in codes:
            problems.append(f"missing finding {w}: {codes}")
    for ok in ("intro", "title", "after", "loose"):
        if any(c == ok for _, c in codes):
            problems.append(f"{ok} should pass: {codes}")
    late = next((f for f in findings if f.get("clip") == "late" and f["edge"] == "start"), None)
    if not late or late["off_ms"] != 150 or abs(late["nearest"] - 2.1) > 1e-9:
        problems.append(f"late start should be 150 ms after the beat at 2.1 s: {late}")
    if sum(1 for c, _ in codes if c == "tween_off_beat") != 1:
        problems.append("only the tween at 1.95 s is off the beat (1.7, 0.1 and 2.1 are on it)")
    if sum(1 for c, _ in codes if c == "eased_slide") != 1:
        problems.append("the expo.out move must not count as an in-out slide")
    print(f"{len(findings)} findings: {codes}")
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
