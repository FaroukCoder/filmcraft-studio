"""Studio jobs: raw footage in -> versioned edits out. Nothing is ever overwritten.

    python -m studio.job talking-head <video> [--style talking-head-default]
    python -m studio.job dj <camera.mp4> <serato-recording.wav>

Job folder (E:/AI/studio-jobs/<name>/): analysis cache, edl.v<N>.json, project.v<N>.fcproj,
render.v<N>.mp4, report.v<N>.json."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from . import analyze, build, plan, reframe, virality

JOBS = Path(r"E:\AI\studio-jobs")


def _next_version(job: Path) -> int:
    done = [int(m[1]) for p in job.glob("edl.v*.json") if (m := re.search(r"v(\d+)", p.name))]
    return max(done, default=0) + 1


def talking_head(video: Path, style: str = "talking-head-default", name: str | None = None) -> dict:
    t0 = time.time()
    job = JOBS / (name or re.sub(r"[^\w-]", "_", video.stem if video.stem != "video" else video.parent.name))
    job.mkdir(parents=True, exist_ok=True)
    info = analyze.probe(video)
    ws = analyze.words(video, job / "words.json")
    st = plan.get_style(style)
    segs = analyze.speech_segments(ws, st["max_gap"], st["pad"], duration=info["duration"])
    crop = plan.crop_fraction(info["width"], info["height"])
    centres = reframe.segment_centres(video, segs, crop) if crop else None
    edl = plan.plan_talking_head(str(video), info, ws, segs, style, centres)
    v = _next_version(job)
    (job / f"edl.v{v}.json").write_text(json.dumps(edl, indent=1), encoding="utf-8")
    counts = build.build(edl, job / f"project.v{v}.fcproj")
    build.export(job / f"project.v{v}.fcproj", job / f"render.v{v}.mp4")
    report = {"version": v, "source": str(video), "style": style, "at": datetime.now().isoformat(timespec="seconds"),
              "source_seconds": info["duration"], "edited_seconds": round(counts["duration"], 2),
              "removed_seconds": round(info["duration"] - counts["duration"], 2),
              "cuts": len(edl["segments"]), "captions": counts["captions"],
              "words": len(ws), "fillers_removed": sum(analyze.is_filler(w["w"]) for w in ws),
              "took_seconds": round(time.time() - t0, 1), "render": str(job / f"render.v{v}.mp4"),
              "virality": virality.score(edl, job / f"render.v{v}.mp4")}
    (job / f"report.v{v}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def dj_set(camera: Path, audio: Path, top: int = 3, name: str | None = None) -> dict:
    """Camera video + clean Serato recording -> the best drop moments, each its own clip:
    synced picture, clean sound, a "TRACK ID?" hook. Moments the camera didn't film are skipped."""
    from . import dj
    t0 = time.time()
    job = JOBS / (name or re.sub(r"[^\w-]", "_", camera.stem))
    job.mkdir(parents=True, exist_ok=True)
    cam_info = analyze.probe(camera)
    clean = dj.load_audio(audio)
    offset, conf = dj.sync_offset(clean, dj.load_audio(camera))
    if conf < 8:
        raise RuntimeError(f"camera/recording sync is unreliable (confidence {conf}); is this the same set?")
    filmed = [m for m in dj.moments(clean, top=top * 3)
              if m["start"] >= offset and m["end"] <= offset + cam_info["duration"]][:top]
    v, renders = _next_version(job), []
    crop = plan.crop_fraction(cam_info["width"], cam_info["height"])
    for n, m in enumerate(filmed, 1):
        cam_in = m["start"] - offset
        keys = [] if not crop else [  # follow the DJ through the clip (times relative to it)
            (round(t - cam_in, 3), c) for t, c in
            reframe.keyframes(reframe.follow(reframe.faces(camera, cam_in, cam_in + m["end"] - m["start"]), crop))]
        edl = {"version": 1, "kind": "dj-drop", "camera": str(camera), "audio": str(audio),
               "src_size": [cam_info["width"], cam_info["height"]], "reframe": keys,
               "size": [1080, 1920], "fps": 30, "moment": m, "sync": {"offset": offset, "confidence": conf},
               "cam_in": round(m["start"] - offset, 4), "audio_in": m["start"],
               "duration": round(m["end"] - m["start"], 4),
               # the animated TRACK ID? stamp slams in exactly on the drop
               "graphics": [{"template": "track-id", "params": {"text": "TRACK ID?"},
                             "start": round(m["at"] - m["start"], 3), "duration": 2.5, "track": "V2"}],
               "base_scale": plan.base_scale(cam_info["width"], cam_info["height"]),
               "segments": [{"start": 0, "src_in": 0, "src_out": round(m["end"] - m["start"], 4), "zoom": 1.0}],
               "captions": [{"start": 0.0, "end": round(m["end"] - m["start"], 4), "text": "TRACK ID?"}]}
        stem = f"drop{n}.v{v}"
        (job / f"edl.{stem}.json").write_text(json.dumps(edl, indent=1), encoding="utf-8")
        build.build_dj(edl, job / f"project.{stem}.fcproj")
        build.export(job / f"project.{stem}.fcproj", job / f"render.{stem}.mp4")
        renders.append({"render": str(job / f"render.{stem}.mp4"), "drop_at": m["at"], "bpm": m["bpm"],
                        "score": m["score"], "virality": virality.score(edl, job / f"render.{stem}.mp4")["total"]})
    (job / f"edl.v{v}.json").write_text(json.dumps({"moments": filmed}, indent=1), encoding="utf-8")
    report = {"version": v, "camera": str(camera), "audio": str(audio), "sync_offset": offset,
              "sync_confidence": conf, "clips": renders, "took_seconds": round(time.time() - t0, 1)}
    (job / f"report.v{v}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "talking-head":
        style = sys.argv[sys.argv.index("--style") + 1] if "--style" in sys.argv else "talking-head-default"
        print(json.dumps(talking_head(Path(sys.argv[2]), style), indent=1))
    elif len(sys.argv) >= 4 and sys.argv[1] == "dj":
        print(json.dumps(dj_set(Path(sys.argv[2]), Path(sys.argv[3])), indent=1))
    else:
        sys.exit(__doc__)
