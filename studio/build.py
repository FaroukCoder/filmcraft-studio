"""Compile an EDL into a FilmCraft project (commands only) and export it (CPU rendering)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import reframe
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
            scale = round(edl["base_scale"] * s["zoom"], 2)
            fc.run("effects.setParam", clip=clips["clips"][0], effect="motion", param="scale", value=scale)
            if "x" in s:  # follow the speaker in a wide source instead of a blind centre crop
                fc.run("effects.setParam", clip=clips["clips"][0], effect="motion", param="position",
                       value=[reframe.position_x(s["x"], edl["src_size"][0], scale, w), h / 2])
        add_captions(fc, edl)
        fc.run("file.saveAs", path=str(project))
        seq = fc.sequence()
    return {"clips": sum(len(t["items"]) for t in seq["video"]), "captions": len(edl["captions"]),
            "duration": seq["duration"] / 254_016_000_000}


def add_captions(fc, edl: dict) -> None:
    """The EDL's captions on a burned-in caption track (C1), in its caption_style."""
    if not edl.get("captions"):
        return
    fc.run("captions.newTrack", format="Subtitle", name="Captions")
    fc.run("captions.setStyle", track="C1", **edl["caption_style"])
    fps = edl["fps"]
    for c in edl["captions"]:
        # frame-exact start in ticks (seconds like 4.8333 land a hair inside the previous
        # caption -> "a caption already covers this time"); end 2 ms short of the boundary
        f0, f1 = round(c["start"] * fps), round(c["end"] * fps)
        fc.run("captions.add", track="C1", text=c["text"], time=f0 * TICKS // fps,
               durationSeconds=(f1 - f0) / fps - 0.002)


def place_graphics(fc, edl: dict, project: Path) -> None:
    """EDL "graphics": [{"template", "params", "start", "duration", "track"}] -> code motion
    graphics rendered to transparent frames (next to the project) and placed on their track."""
    from . import mograph
    for n, g in enumerate(edl.get("graphics", []), 1):
        frames = project.parent / f"{project.stem}.gfx{n}"
        html = g["html"] if "html" in g else mograph.template_html(g["template"], tuple(edl["size"]),
                                                                   pack=edl.get("pack", mograph.PACK),
                                                                   **g.get("params", {}))
        mograph.render(html, frames, g["duration"], edl["fps"], tuple(edl["size"]))
        mograph.place(fc, frames, g["start"], g.get("track", "V2"))


SNAP_FRAMES = 15  # settle after the snap (motion.md: 9-18 f)


def snap_keys(at: float, base: float, fps: int, end: float, snap: float = 1.07) -> list[tuple[float, float]]:
    """Scale keyframes for a camera snap at `at`: one frame to `snap` x base, then an exponential
    settle to 1.02 x base over SNAP_FRAMES (a key per frame, so linear interpolation between keys
    traces the curve). Times are sequence seconds, clipped to the part's `end`."""
    keys = [(at - 1 / fps, base)] if at > 0 else []
    for f in range(SNAP_FRAMES + 1):
        k = 2 ** (-10 * f / SNAP_FRAMES)  # share of the snap still left (expo-out settle)
        keys.append((at + f / fps, round(base * (1.02 + (snap - 1.02) * k), 3)))
    return [(round(t, 4), v) for t, v in keys if t < end]


def build_dj(edl: dict, project: Path) -> dict:
    """A DJ moment: the camera's picture (no sound) over the clean recording's audio, synced,
    with a hook title. EDL (plan.plan_dj_clip): {"camera", "audio", "parts": [{"start",
    "cam_in", "audio_in", "duration", "reframe"?}], "duration", "title"?, "graphics", ...}."""
    w, h = edl["size"]
    with Session() as fc:
        fc.run("file.newSequence", name=project.stem, width=w, height=h, fps=edl["fps"])
        cam, aud = fc.run("file.import", paths=[edl["camera"], edl["audio"]])["items"][:2]
        for p in edl["parts"]:
            clip = fc.run("timeline.place", item=cam, track="V1", time=ticks(p["start"]),
                          sourceIn=ticks(p["cam_in"]), duration=ticks(p["duration"]), audio=False)["clips"][0]
            fc.run("effects.setParam", clip=clip, effect="motion", param="scale", value=edl["base_scale"])
            for at in edl.get("snaps", []):  # the camera snaps in on the drop, then settles
                if p["start"] <= at < p["start"] + p["duration"]:
                    for t, v in snap_keys(at, edl["base_scale"], edl["fps"], p["start"] + p["duration"]):
                        fc.run("effects.setParam", clip=clip, effect="motion", param="scale",
                               value=v, time=ticks(t), keyframe=True)
            for t, x in p.get("reframe", []):  # keyframed camera that follows the DJ; `time` is
                fc.run("effects.setParam", clip=clip, effect="motion", param="position",  # sequence time
                       value=[reframe.position_x(x, edl["src_size"][0], edl["base_scale"], w), h / 2],
                       time=ticks(p["start"] + t), keyframe=True)
            fc.run("timeline.place", item=aud, track="A1", time=ticks(p["start"]),
                   sourceIn=ticks(p["audio_in"]), duration=ticks(p["duration"]))  # the sound alone
        if edl.get("title"):  # a static FilmCraft title (graphics below are the animated kind)
            fc.run("graphics.newText", text=edl["title"], position=[w // 2, round(h * 0.2)], size=120,
                   seconds=edl["duration"], time=0, newClip=True)
            fc.run("graphics.set", props={"align": "center", "font_style": "Bold"})
        place_graphics(fc, edl, project)
        add_captions(fc, edl)  # the hook caption: on screen until the drop graphic takes over
        fc.run("file.saveAs", path=str(project))
        seq = fc.sequence()
    return {"clips": sum(len(t["items"]) for t in seq["video"]), "duration": seq["duration"] / TICKS}


def export(project: Path, out: Path, grade: str | None = None) -> None:
    """H.264, burned captions, loudness normalised to -14 LUFS (the social-platform target),
    CPU rendering (the GPU is unstable under sustained load)."""
    # --settings is ExportSettings JSON (a flat "loudnessLufs" there is silently ignored). The
    # ceiling sits 1.5 dB under the -1 dBTP QA limit: the AAC encode overshoots the limiter ~1 dB.
    settings = '{"burnCaptions": true, "effects": {"loudness": {"enabled": true, "target_lufs": -14, "true_peak_dbtp": -2.5}}}'
    r = subprocess.run([str(CLI), "--project", str(project), "export", str(out),
                        "--gpu-rendering", "off", "--settings", settings],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"export failed ({r.returncode}): {r.stdout[-800:]} {r.stderr[-800:]}")
    if grade:  # the pack's footage grade over the finished picture; sound copied untouched
        raw = out.with_name(out.stem + ".ungraded.mp4")
        out.replace(raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vf", grade, "-c:v", "libx264",
                        "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy",
                        "-movflags", "+faststart", str(out)], check=True)
        raw.unlink()
