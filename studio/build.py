"""Compile an EDL into a FilmCraft project (commands only) and export it (CPU rendering)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .fc import CLI, TICKS, Session, ticks


def build(edl: dict, project: Path) -> dict:
    """Write `project` (.fcproj) from the EDL. Returns counts for the job report."""
    w, h = edl["size"]
    with Session() as fc:
        fc.run("file.newSequence", name=project.stem, width=w, height=h, fps=edl["fps"])
        item = fc.run("file.import", paths=[edl["source"]])["items"][0]
        for s in edl["segments"]:
            clips = fc.run("timeline.place", item=item, track="V1", time=ticks(s["start"]),
                           sourceIn=ticks(s["src_in"]), duration=ticks(s["src_out"] - s["src_in"]))
            fc.run("effects.setParam", clip=clips["clips"][0], effect="motion", param="scale",
                   value=round(edl["base_scale"] * s["zoom"], 2))
        if edl["captions"]:
            fc.run("captions.newTrack", format="Subtitle", name="Captions")
            fc.run("captions.setStyle", track="C1", **edl["caption_style"])
            fps = edl["fps"]
            for c in edl["captions"]:
                # frame-exact start in ticks (seconds like 4.8333 land a hair inside the previous
                # caption -> "a caption already covers this time"); end 2 ms short of the boundary
                f0, f1 = round(c["start"] * fps), round(c["end"] * fps)
                fc.run("captions.add", track="C1", text=c["text"], time=f0 * TICKS // fps,
                       durationSeconds=(f1 - f0) / fps - 0.002)
        fc.run("file.saveAs", path=str(project))
        seq = fc.sequence()
    return {"clips": sum(len(t["items"]) for t in seq["video"]), "captions": len(edl["captions"]),
            "duration": seq["duration"] / 254_016_000_000}


def place_graphics(fc, edl: dict, project: Path) -> None:
    """EDL "graphics": [{"template", "params", "start", "duration", "track"}] -> code motion
    graphics rendered to transparent frames (next to the project) and placed on their track."""
    from . import mograph
    for n, g in enumerate(edl.get("graphics", []), 1):
        frames = project.parent / f"{project.stem}.gfx{n}"
        html = g["html"] if "html" in g else mograph.template_html(g["template"], tuple(edl["size"]),
                                                                   **g.get("params", {}))
        mograph.render(html, frames, g["duration"], edl["fps"], tuple(edl["size"]))
        mograph.place(fc, frames, g["start"], g.get("track", "V2"))


def build_dj(edl: dict, project: Path) -> dict:
    """A DJ moment: the camera's picture (no sound) over the clean recording's audio, synced,
    with a hook title. EDL: {"camera", "audio", "cam_in", "audio_in", "duration", "title", ...}."""
    w, h = edl["size"]
    with Session() as fc:
        fc.run("file.newSequence", name=project.stem, width=w, height=h, fps=edl["fps"])
        cam, aud = fc.run("file.import", paths=[edl["camera"], edl["audio"]])["items"][:2]
        clips = fc.run("timeline.place", item=cam, track="V1", time=0, sourceIn=ticks(edl["cam_in"]),
                       duration=ticks(edl["duration"]), audio=False)
        fc.run("effects.setParam", clip=clips["clips"][0], effect="motion", param="scale",
               value=edl["base_scale"])
        fc.run("timeline.place", item=aud, track="A1", time=0, sourceIn=ticks(edl["audio_in"]),
               duration=ticks(edl["duration"]))  # an audio track as `track`: the sound alone
        if edl.get("title"):  # a static FilmCraft title (graphics below are the animated kind)
            fc.run("graphics.newText", text=edl["title"], position=[w // 2, round(h * 0.2)], size=120,
                   seconds=edl["duration"], time=0, newClip=True)
            fc.run("graphics.set", props={"align": "center", "font_style": "Bold"})
        place_graphics(fc, edl, project)
        fc.run("file.saveAs", path=str(project))
        seq = fc.sequence()
    return {"clips": sum(len(t["items"]) for t in seq["video"]), "duration": seq["duration"] / TICKS}


def export(project: Path, out: Path) -> None:
    """H.264, burned captions, loudness normalised to -14 LUFS (the social-platform target),
    CPU rendering (the GPU is unstable under sustained load)."""
    r = subprocess.run([str(CLI), "--project", str(project), "export", str(out),
                        "--gpu-rendering", "off", "--settings", '{"burnCaptions": true, "loudnessLufs": -14}'],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"export failed ({r.returncode}): {r.stdout[-800:]} {r.stderr[-800:]}")
