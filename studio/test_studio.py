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

# virality rubric: band scoring and the measured items on a small EDL
from studio import virality  # noqa: E402
assert virality._band(30, 15, 45, 30) == 10 and virality._band(75, 15, 45, 30) == 0 and virality._band(60, 15, 45, 30) == 5
v = virality.score({"segments": [{"start": 0, "src_in": 0, "src_out": 10, "zoom": 1.12},
                                 {"start": 10, "src_in": 12, "src_out": 20, "zoom": 1.0}],
                    "captions": [{"start": 0.2, "end": 2.0, "text": "WHAT'S THE ID?"}]})
assert v["items"]["hook"]["score"] == 10 and v["items"]["comment_trigger"]["score"] == 10
assert v["items"]["payoff_loop"]["score"] is None and v["items"]["audio"]["score"] is None
assert v["total"] is not None and 0 <= v["total"] <= 10
print("ok")

# pacing: a boundary that is both a cut and a zoom change counts once
pv = virality.score({"segments": [{"start": 0, "src_in": 0, "src_out": 5, "zoom": 1.12},
                                  {"start": 5, "src_in": 6, "src_out": 10, "zoom": 1.0}], "captions": []})
assert pv["items"]["pacing"]["why"].startswith("1.1 changes/10s"), pv["items"]["pacing"]
print("ok")

# style packs: fast, upper-case, low-caption references -> tight cuts, caps, bottom anchor
from studio import reference  # noqa: E402
fast = {"cuts_per_10s": 6, "median_shot": 1.2, "words_per_second": 3, "brightness": 90, "saturation": 30,
        "caption_frames": 0.9, "words_per_caption": 2, "uppercase": 0.9, "caption_y": 0.8}
st = reference.to_style([fast, {**fast, "cuts_per_10s": 5}])
assert st["max_gap"] == 0.25 and st["uppercase"] and st["words_per_caption"] == 2
assert st["caption_style"]["anchor"] == "bottom" and st["punch_in"] == 1.15
slow = reference.to_style([{**fast, "cuts_per_10s": 1, "uppercase": 0.1, "caption_y": 0.5}])
assert slow["max_gap"] == 0.5 and not slow["uppercase"] and slow["caption_style"]["anchor"] == "middle"
print("ok")

# pace from the pauses the references left in: tight editors -> tight max_gap (clamped 0.15-0.6)
ws_tight = [W(f"w{i}", i * 0.3, i * 0.3 + 0.25) for i in range(20)]  # 0.05 s gaps
assert reference.p90_word_gap(ws_tight) == 0.05
assert reference.to_style([{**fast, "p90_word_gap": 0.05}])["max_gap"] == 0.15
assert reference.to_style([{**fast, "p90_word_gap": 0.3, "cuts_per_10s": 1}])["max_gap"] == 0.4
print("ok")

# motion-graphics templates: text is HTML-escaped, words staggered, background transparent
from studio import mograph  # noqa: E402
h = mograph.template_html("kinetic-title", text="A <b> C", accent="#ff0000")
assert "&lt;b&gt;" in h and "<b>" not in h.split("<body>")[1]
assert h.count('class="w"') == 3 and "animation-delay:0.28s" in h
assert "background:transparent" in h and "#ff0000" in h
assert "TRACK ID?" in mograph.template_html("track-id", text="TRACK ID?")
print("ok")
