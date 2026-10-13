"""Studio jobs: raw footage in -> versioned edits out. Nothing is ever overwritten.

    python -m studio.job talking-head <video> [--style talking-head-default]
    python -m studio.job dj <camera.mp4> <serato-recording.wav> [--llm rules|local|claude]
    python -m studio.job promo "<brief>" [--seconds 20] [--music bed.mp3] [--llm local|claude]
    python -m studio.job promo - --storyboard board.json [--music bed.mp3]

Job folder (E:/AI/studio-jobs/<name>/): analysis cache, edl.v<N>.json, project.v<N>.fcproj,
render.v<N>.mp4, report.v<N>.json."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from . import analyze, build, llm, plan, qa, reframe, virality

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
              "virality": virality.score(edl, job / f"render.v{v}.mp4"),
              "qa": qa.check(job / f"render.v{v}.mp4", edl, counts["duration"])}
    (job / f"report.v{v}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def dj_set(camera: Path, audio: Path, top: int = 3, name: str | None = None, provider: str | None = None) -> dict:
    """Camera video + clean Serato recording -> the best drop moments, 3 variants each (synced
    picture, clean sound, hook caption, drop graphic), judged and ranked. The director plans with
    `provider` (llm.PROVIDER by default; "rules" = no LLM). Unfilmed moments are skipped."""
    from . import director, dj
    t0 = time.time()
    job = JOBS / (name or re.sub(r"[^\w-]", "_", camera.stem))
    job.mkdir(parents=True, exist_ok=True)
    cam_info = analyze.probe(camera)
    clean = dj.load_audio(audio)
    offset, conf = dj.sync_offset(clean, dj.load_audio(camera))
    if conf < dj.SYNC_MIN_CONF:  # true matches 24+, another recording <= 5 (test_sync benchmark)
        raise RuntimeError(f"camera/recording sync is unreliable (confidence {conf}); is this the same set?")
    filmed = [m for m in dj.moments(clean, top=top * 3)
              if m["start"] >= offset and m["end"] <= offset + cam_info["duration"]]
    v = _next_version(job)
    direction = director.plan_dj(filmed, n=top, provider=provider)
    crop = plan.crop_fraction(cam_info["width"], cam_info["height"])
    clips = []
    for n, pick in enumerate(direction["picks"], 1):
        m = filmed[pick["moment"]]
        bar = 4 * 60 / m["bpm"]
        faces = reframe.faces(camera, max(0.0, m["at"] - 8 * bar - offset), m["at"] + 18 * bar - offset) if crop else []
        facts, rows = {}, []
        for var in pick["variants"]:
            edl = plan.plan_dj_clip(m, offset, str(camera), str(audio), cam_info, var["tease_bars"],
                                    var["before_bars"], var["after_bars"], var["hook_text"], var["stamp"])
            if any(p["cam_in"] < 0 or p["cam_in"] + p["duration"] > cam_info["duration"] for p in edl["parts"]):
                continue  # this cut reaches past what the camera filmed
            edl.update(sync={"offset": offset, "confidence": conf}, variant=var)
            for p in edl["parts"] if crop else []:  # follow the DJ (key times relative to the part)
                span = [(t, x) for t, x in faces if p["cam_in"] <= t <= p["cam_in"] + p["duration"]]
                p["reframe"] = [(round(t - p["cam_in"], 3), c) for t, c in reframe.keyframes(reframe.follow(span, crop))]
            stem = f"drop{n}.v{v}.{var['name']}"
            (job / f"edl.{stem}.json").write_text(json.dumps(edl, indent=1), encoding="utf-8")
            build.build_dj(edl, job / f"project.{stem}.fcproj")
            render = job / f"render.{stem}.mp4"
            build.export(job / f"project.{stem}.fcproj", render)
            check = qa.check(render, edl, edl["duration"])
            facts[var["name"]] = {"render": str(render), "seconds": edl["duration"], "drop_at": edl["drop_at"],
                                  "rubric": virality.score(edl, render)["total"], "qa": check["problems"]}
            rows.append((var["name"], render, director.frame_times(edl)))
        if not rows:
            continue
        sheet = director.contact_sheet(rows, job / f"sheet.drop{n}.v{v}.png")
        verdict = None
        if direction["provider"] != "rules":
            try:
                verdict = director.judge(sheet, facts, provider=provider)
            except (llm.LLMError, OSError, ValueError) as exc:
                verdict = {"error": str(exc)[:200]}
        clips.append({"moment": m, "why": pick["why"], "sheet": str(sheet), "variants": facts,
                      "judge": verdict, "ranking": director.rank(facts, verdict if verdict and "scores" in verdict else None)})
    (job / f"edl.v{v}.json").write_text(json.dumps({"moments": filmed, "direction": direction}, indent=1), encoding="utf-8")
    report = {"version": v, "camera": str(camera), "audio": str(audio), "sync_offset": offset,
              "sync_confidence": conf, "planner": {k: direction.get(k) for k in ("provider", "model", "fallback_reason")},
              "clips": clips, "took_seconds": round(time.time() - t0, 1)}
    (job / f"report.v{v}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def promo_video(brief: str | None = None, storyboard: Path | None = None, seconds: int = 20,
                music: Path | None = None, name: str | None = None, provider: str | None = None) -> dict:
    """A motion-graphics video from a brief (the LLM writes the storyboard) or a storyboard file:
    render, QA, contact sheet, then the judge (when an LLM wrote it or `provider` is set)."""
    from . import director, promo
    t0 = time.time()
    if storyboard:
        board = promo._clean_board(json.loads(storyboard.read_text(encoding="utf-8")))
        board.setdefault("provider", "file")
    else:
        board = promo.plan_storyboard(brief, seconds, provider=provider)
    job = JOBS / "promo" / (name or re.sub(r"[^\w-]", "_", (brief or storyboard.stem)[:40]).strip("_"))
    job.mkdir(parents=True, exist_ok=True)
    v = max([int(m[1]) for p in job.glob("board.v*.json") if (m := re.search(r"v(\d+)", p.name))], default=0) + 1
    (job / f"board.v{v}.json").write_text(json.dumps({"brief": brief, **board}, indent=1), encoding="utf-8")
    out = job / f"render.v{v}.mp4"
    result = promo.render_video(board, out, music)
    edl = {"size": [promo.W, promo.H], "fps": promo.FPS}
    check = qa.check(out, edl, result["seconds"])
    problems = check["problems"] + [f"text overflows: {t}" for t in result["overflow"]]
    sheet = director.contact_sheet([(f"v{v}", out, promo.contact_times(board))], job / f"sheet.v{v}.png", thumb_h=480)
    facts = {f"v{v}": {"seconds": result["seconds"], "rubric": None, "qa": problems}}
    verdict = None
    if provider or board.get("provider") not in ("file", "rules"):
        try:
            verdict = director.judge(sheet, {k: {**f, "rubric": "n/a"} for k, f in facts.items()}, provider, kind="promo")
        except (llm.LLMError, OSError, ValueError) as exc:
            verdict = {"error": str(exc)[:200]}
    report = {"version": v, "brief": brief, "storyboard_by": {k: board.get(k) for k in ("provider", "model")},
              "render": str(out), "seconds": result["seconds"], "qa": problems, "sheet": str(sheet),
              "judge": verdict, "took_seconds": round(time.time() - t0, 1)}
    (job / f"report.v{v}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


if __name__ == "__main__":
    flag = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None  # noqa: E731
    if len(sys.argv) >= 3 and sys.argv[1] == "talking-head":
        print(json.dumps(talking_head(Path(sys.argv[2]), flag("--style") or "talking-head-default"), indent=1))
    elif len(sys.argv) >= 4 and sys.argv[1] == "dj":
        print(json.dumps(dj_set(Path(sys.argv[2]), Path(sys.argv[3]), provider=flag("--llm")), indent=1))
    elif len(sys.argv) >= 3 and sys.argv[1] == "promo":
        board = Path(flag("--storyboard")) if flag("--storyboard") else None
        print(json.dumps(promo_video(None if board else sys.argv[2], board, int(flag("--seconds") or 20),
                                     Path(flag("--music")) if flag("--music") else None,
                                     provider=flag("--llm")), indent=1))
    else:
        sys.exit(__doc__)
