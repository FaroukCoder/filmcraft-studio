"""Lint a HyperFrames composition against the music: the "motion grammar on the bar grid".

The house-look rules in the report say things should appear and leave on beats, change on
bar lines, and not drift around on eased slides or typed-out headlines (motionmaxxing's
tells of AI motion graphics). This checks a HyperFrames HTML composition for exactly that:

- every timeline element's start and end (`data-start` / `data-duration`, including
  relative starts like `data-start="intro + 0.5"`) against the beat grid: off by more than
  one frame is a finding; elements marked `data-beat="bar"` must sit on bar lines;
- GSAP calls in inline scripts: a numeric position argument (`tl.to(el, {...}, 1.7)`) off the
  beat grid, movement (`x`, `y`, `xPercent`, `yPercent`) with an in-out ease ("everything is a
  slide"), and typewriter text (TextPlugin `text:`).

    python beat_lint.py index.html --bpm 150 --downbeat 0.112 [--fps 30] [--json]

Exit code 1 when there are findings, so it can sit in your motion-graphics QA step.
HyperFrames' own `hyperframes lint` checks structure; this checks rhythm and taste rules.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class Clip:
    id: str
    start_raw: str
    duration: float | None
    beat: str = "beat"  # beat | bar | off (data-beat="off" opts out)
    start: float | None = None


@dataclass
class Doc:
    clips: list[Clip] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.doc = Doc()
        self._in_script = False
        self._n = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self._in_script = True
            self.doc.scripts.append("")
        if "data-start" in a and tag != "html":
            self._n += 1
            cid = a.get("id") or a.get("data-composition-id") or f"{tag}#{self._n}"
            try:
                dur = float(a["data-duration"]) if a.get("data-duration") not in (None, "") else None
            except ValueError:
                dur = None
            self.doc.clips.append(Clip(cid, a["data-start"].strip(), dur, (a.get("data-beat") or "beat").strip()))

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script and self.doc.scripts:
            self.doc.scripts[-1] += data


def resolve_starts(clips: list[Clip]) -> list[str]:
    """Absolute starts; a clip id means "when that clip ends", optionally +/- seconds."""
    by_id = {c.id: c for c in clips}
    problems = []
    for _ in range(len(clips) + 1):
        changed = False
        for c in clips:
            if c.start is not None:
                continue
            try:
                c.start = float(c.start_raw)
                changed = True
                continue
            except ValueError:
                pass
            m = re.fullmatch(r"([A-Za-z0-9_-]+)\s*(?:([+-])\s*([0-9.]+))?", c.start_raw)
            ref = by_id.get(m.group(1)) if m else None
            if ref and ref.start is not None and ref.duration is not None:
                delta = float(m.group(3) or 0) * (-1 if m.group(2) == "-" else 1)
                c.start = ref.start + ref.duration + delta
                changed = True
        if not changed:
            break
    for c in clips:
        if c.start is None:
            problems.append(f"{c.id}: could not resolve data-start={c.start_raw!r}")
    return problems


def nearest(t: float, period: float, origin: float) -> tuple[float, float]:
    k = round((t - origin) / period)
    g = origin + k * period
    return g, t - g


def gsap_calls(src: str) -> list[str]:
    """Argument text of every .to( / .from( / .fromTo( call, brackets matched (strings skipped)."""
    out = []
    for m in re.finditer(r"\.(?:to|from|fromTo)\s*\(", src):
        depth, i, quote = 1, m.end(), None
        while i < len(src) and depth:
            ch = src[i]
            if quote:
                if ch == "\\":
                    i += 1
                elif ch == quote:
                    quote = None
            elif ch in "'\"`":
                quote = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            i += 1
        out.append(src[m.end(): i - 1])
    return out


def _last_arg(args: str) -> float | None:
    """The timeline position argument (a plain number in seconds), if the call has one."""
    depth, quote, cut = 0, None, -1
    for i, ch in enumerate(args):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            cut = i
    last = args[cut + 1:].strip() if cut >= 0 else ""
    return float(last) if re.fullmatch(r"-?\d+(\.\d+)?", last) else None


def lint(html: str, bpm: float, downbeat: float = 0.0, fps: float = 30.0) -> list[dict]:
    p = _Parser()
    p.feed(html)
    doc = p.doc
    out = [{"code": "unresolved_start", "detail": d} for d in resolve_starts(doc.clips)]
    beat = 60.0 / bpm
    bar = 4 * beat
    tol = 1.0 / fps + 1e-6
    for c in doc.clips:
        if c.start is None or c.beat == "off":
            continue
        period = bar if c.beat == "bar" else beat
        marks = [("start", c.start)] + ([("end", c.start + c.duration)] if c.duration is not None else [])
        for what, t in marks:
            g, off = nearest(t, period, downbeat)
            if abs(off) > tol:
                out.append({"code": f"off_{c.beat}", "clip": c.id, "edge": what, "time": round(t, 3),
                            "nearest": round(g, 3), "off_ms": round(off * 1000)})
    for i, src in enumerate(doc.scripts):
        for body in gsap_calls(src):
            moves = re.search(r"\b(x|y|xPercent|yPercent)\s*:", body)
            ease = re.search(r"ease\s*:\s*['\"]([^'\"]+)['\"]", body)
            if moves and ease and "inout" in ease.group(1).lower().replace(".", ""):
                out.append({"code": "eased_slide", "script": i, "ease": ease.group(1),
                            "detail": "movement with an in-out ease reads as a template slide; cut, or move on a bar line with a linear/out ease"})
            pos = _last_arg(body)
            if pos is not None:
                g, off = nearest(pos, beat, downbeat)
                if abs(off) > tol:
                    out.append({"code": "tween_off_beat", "script": i, "time": pos, "nearest": round(g, 3),
                                "off_ms": round(off * 1000)})
            if re.search(r"\btext\s*:\s*[{'\"`]", body):
                out.append({"code": "typewriter_text", "script": i,
                            "detail": "typed-out text is one of the tells of AI motion graphics; set the line, or cut word by word on beats"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("html")
    ap.add_argument("--bpm", type=float, required=True)
    ap.add_argument("--downbeat", type=float, default=0.0, help="time of a downbeat in composition seconds")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    findings = lint(open(args.html, encoding="utf-8").read(), args.bpm, args.downbeat, args.fps)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['code']:18s} " + ", ".join(f"{k}={v}" for k, v in f.items() if k != "code"))
        print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
