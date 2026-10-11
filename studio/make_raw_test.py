"""Make a synthetic "raw" talking-head take from an edited reel, so the jump-cut logic has real
pauses to remove: after every sentence it inserts a frozen frame with 1.2 s of silence.
python -m studio.make_raw_test <video> <words.json> <out.mp4>"""
import json
import re
import subprocess
import sys
from pathlib import Path


def main(video: str, words: str, out: str, pause: float = 1.2) -> None:
    ws = json.loads(Path(words).read_text(encoding="utf-8"))
    cuts, start = [], 0.0  # sentence ends (word ending in . ! ?) -> split points
    for w in ws:
        if re.search(r"[.!?]$", w["w"]):
            cuts.append((start, w["end"]))
            start = w["end"]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", video], capture_output=True, text=True).stdout)
    cuts.append((start, dur))
    parts, fil = [], []
    for i, (a, b) in enumerate(cuts):
        fil.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={pause}[v{i}];"
                   f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,apad=pad_dur={pause}[a{i}];")
        parts.append(f"[v{i}][a{i}]")
    graph = "".join(fil) + "".join(parts) + f"concat=n={len(cuts)}:v=1:a=1[v][a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-filter_complex", graph, "-map", "[v]",
                    "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", out],
                   check=True)
    print(f"{out}: {len(cuts)} sentences, {len(cuts) * pause:.1f}s of pauses added")


if __name__ == "__main__":
    main(*sys.argv[1:4])
