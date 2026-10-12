"""Studio jobs: raw footage in -> versioned edits out. Nothing is ever overwritten.

    python -m studio.job talking-head <video> [--style talking-head-default]

Job folder (E:/AI/studio-jobs/<name>/): analysis cache, edl.v<N>.json, project.v<N>.fcproj,
render.v<N>.mp4, report.v<N>.json."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from . import analyze, build, plan, virality

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
    edl = plan.plan_talking_head(str(video), info, ws, segs, style)
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


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "talking-head":
        sys.exit(__doc__)
    style = sys.argv[sys.argv.index("--style") + 1] if "--style" in sys.argv else "talking-head-default"
    print(json.dumps(talking_head(Path(sys.argv[2]), style), indent=1))
