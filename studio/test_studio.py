"""Self-checks for the pure logic (no FilmCraft, no Whisper): python -m studio.test_studio"""
from studio import analyze, plan
from studio.fc import TICKS, ticks

W = lambda w, a, b: {"w": w, "start": a, "end": b}  # noqa: E731

# speech segments: a long pause splits, a filler is dropped, padding merges near words
ws = [W("Hello", 0.5, 0.9), W("there", 0.95, 1.3), W("um", 1.5, 1.8), W("so", 2.6, 2.8),
      W("today", 2.85, 3.3)]
segs = analyze.speech_segments(ws, max_gap=0.35, pad=0.08, duration=4.0)
assert segs == [(0.42, 1.38), (2.52, 3.38)], segs
assert analyze.is_filler("Um,") and not analyze.is_filler("like")

# captions: max 3 words, break after punctuation
ch = plan.caption_chunks([W("one", 0, 1), W("two.", 1, 2), W("three", 2, 3), W("four", 3, 4),
                          W("five", 4, 5), W("six", 5, 6)], 3, 18)
assert [[w["w"] for w in c] for c in ch] == [["one", "two."], ["three", "four", "five"], ["six"]]

# plan: segments laid back to back, punch-in alternates on real cuts, captions in timeline time
edl = plan.plan_talking_head("x.mp4", {"width": 1080, "height": 1920}, ws, segs)
assert [s["start"] for s in edl["segments"]] == [0.0, 0.96]
assert [s["zoom"] for s in edl["segments"]] == [1.12, 1.0]
assert edl["captions"][0]["text"] == "HELLO THERE" and edl["captions"][0]["start"] == round(2 / 30, 4)
assert edl["captions"][1]["start"] == round(round((2.6 - 2.52 + 0.96) * 30) / 30, 4)  # after the cut
assert all(a["end"] <= b["start"] for a, b in zip(edl["captions"], edl["captions"][1:]))

# frame snapping: captions touching in seconds must not overlap once snapped to frames
snapped = plan.frame_snap([{"start": 20.0, "end": 20.36, "text": "a"},
                           {"start": 20.36, "end": 21.0, "text": "b"},
                           {"start": 21.01, "end": 21.012, "text": "too short"}], fps=30)
assert snapped[0]["end"] <= snapped[1]["start"] and len(snapped) == 2

# vertical fill: a 16:9 source is scaled to fill 1920 high; a 9:16 source stays 100%
assert plan.base_scale(1920, 1080) == 177.78 and plan.base_scale(1080, 1920) == 100.0
assert ticks(1.5) == TICKS * 3 // 2
print("ok")
