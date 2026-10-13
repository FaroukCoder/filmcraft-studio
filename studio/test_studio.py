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
h = mograph.template_html("kinetic-title", text="A <b> C")
assert "&lt;b&gt;" in h and "<b>" not in h.split("<body>")[1].split("<script>")[0]
assert h.count('class="mask"') == 3 and "animation-delay:0.167s" in h  # uneven onsets: 0, 3, 5 frames
assert "background:transparent" in h and "Archivo" in h and "file:///" in h  # club pack, local fonts
assert "uppercase" not in h and "michroma" in mograph.template_html("name", text="x", pack="house").lower()
assert mograph.template_html("name", text="Sara Landry").count("sara landry") == 1  # lowercase name
assert mograph.pack_grade("club").startswith("eq=") and mograph.pack_grade("house")
print("ok")

# reframe: the virtual camera holds inside the deadzone, eases toward a drifting face, cuts on a
# jump, holds when the face is lost, starts centred before any face, and stays inside the source
from studio import reframe  # noqa: E402
crop = plan.crop_fraction(1920, 1080)
assert crop == 0.3164 and plan.crop_fraction(1080, 1920) is None
path = reframe.follow([(0, None), (0.25, 0.30), (0.5, 0.32), (0.75, 0.45), (1.0, None), (1.25, 0.85)], crop)
cams = [c for _, c in path]
assert cams[0] == cams[1] == 0.30 and cams[2] == 0.30          # first sight; 0.02 is inside the deadzone
assert 0.30 < cams[3] < 0.45 and cams[4] == cams[3]             # eased catch-up; lost face -> hold
assert cams[5] == round(1 - crop / 2, 4)                        # jump -> cut, clamped to the edge
keys = reframe.keyframes(path)
assert keys[-2] == (round(1.25 - 1 / 30, 4), cams[4]) and keys[-1] == (1.25, cams[5])  # hold key, no whip pan
# position: the source centre's place in the frame; centred subject -> centred; never past an edge
assert reframe.position_x(0.5, 1920, 177.78) == 540.0
assert reframe.position_x(0.0, 1920, 177.78) == round(540 + (1920 * 1.7778 - 1080) / 2, 1)
assert reframe.position_x(0.3, 1920, 177.78) == round(540 + 0.2 * 1920 * 1.7778, 1)
print("ok")

# post-render QA: detector spans and the true peak parse out of an ffmpeg log
from studio import qa  # noqa: E402
log = ("[blackdetect @ 0] black_start:0 black_end:0.8 black_duration:0.8\n"
       "[freezedetect @ 0] lavfi.freezedetect.freeze_start: 3.5\n"
       "[silencedetect @ 0] silence_start: -0.01\n[silencedetect @ 0] silence_end: 2 | silence_duration: 2\n"
       "  True peak:\n    Peak:       -0.4 dBFS\n")
d = qa.parse(log)
assert d["black"] == [(0.0, 0.8)] and d["freeze"] == [(3.5, None)] and d["silence"] == [(0.0, 2.0)]
assert d["true_peak"] == -0.4 and qa.parse("    Peak:       -inf dBFS")["true_peak"] is None
print("ok")

# DJ clip: a one-bar flash-forward of the drop opens the clip, then the build-up plays through;
# cuts on bar lines, the DJ's name lands on the real drop, the camera snaps there and at 0 (the tease
# opens on the drop), the rubric hook is the drop
m = {"start": 100.0, "at": 107.5, "end": 122.5, "bpm": 128.0}  # 4 bars before, 8 after at 128 BPM
cam = {"width": 1920, "height": 1080}
e = plan.plan_dj_clip(m, offset=40.0, camera="c.mp4", audio="a.wav", cam_info=cam, dj="Sara Landry")
bar = 4 * 60 / 128
assert e["tease"] == round(bar, 4) and e["drop_at"] == 0.0
assert e["parts"][0] == {"start": 0.0, "audio_in": 107.5, "cam_in": 67.5, "duration": round(bar, 4)}
assert e["parts"][1]["start"] == e["tease"] and e["parts"][1]["audio_in"] == 100.0 and e["parts"][1]["cam_in"] == 60.0
assert e["graphics"][0]["start"] == round(bar + 7.5, 3) and e["duration"] == round(bar + 22.5, 4)
assert e["graphics"][0]["template"] == "name" and e["snaps"] == [0.0, round(bar + 7.5, 3)] and e["captions"] == []
assert virality.score(e)["items"]["hook"]["score"] == 10
plain = plan.plan_dj_clip(m, 40.0, "c.mp4", "a.wav", cam, tease_bars=0)
assert len(plain["parts"]) == 1 and plain["drop_at"] == 7.5 and virality.score(plain)["items"]["hook"]["score"] == 0
print("ok")

# director: an LLM plan is cleaned (bad index, duplicate moment, long caption, clashing names),
# a failing LLM falls back to the rules plan, and the ranking puts QA failures last
from studio import director, llm  # noqa: E402
moms = [{"at": 100.0, "bpm": 145.0, "score": 3.0, "break": 16.0, "start": 93.4, "end": 113.2},
        {"at": 300.0, "bpm": 145.0, "score": 9.0, "break": 30.0, "start": 293.4, "end": 313.2}]
V = lambda name, stamp="name": {"name": name, "tease_bars": 1, "before_bars": 4, "after_bars": 8,  # noqa: E731
                                "stamp": stamp}
messy = {"picks": [{"moment": 7, "why": "x", "variants": [V("a"), V("b"), V("c")]},
                   {"moment": 1, "why": "big", "variants": [V("Hard Hit!"), V("hard hit"), V("c", "none")]},
                   {"moment": 1, "why": "dup", "variants": [V("a"), V("b"), V("c")]}]}
real_ask = llm.ask
llm.ask = lambda *a, **k: {"data": messy, "provider": "local", "model": "fake"}
d = director.plan_dj(moms, n=3, provider="local")
assert [p["moment"] for p in d["picks"]] == [1] and d["model"] == "fake"
names = [v["name"] for v in d["picks"][0]["variants"]]
assert names == ["hard-hit", "hard-hit-2", "c"] and d["picks"][0]["variants"][2]["stamp"] == "none"
def boom(*a, **k):
    raise llm.LLMError("Not logged in")
llm.ask = boom
fb = director.plan_dj(moms, n=1, provider="claude")
assert fb["provider"] == "rules" and fb["picks"][0]["moment"] == 1 and "Not logged in" in fb["fallback_reason"]
llm.ask = real_ask
r = director.rank({"a": {"rubric": 9.0, "qa": ["silence 0-2s"]}, "b": {"rubric": 6.0, "qa": []},
                   "c": {"rubric": 7.0, "qa": []}},
                  {"scores": {"b": {"hook": 9, "payoff_loop": 9, "visual": 9, "fix": "-"},
                              "c": {"hook": 5, "payoff_loop": 5, "visual": 5, "fix": "tighter"}}})
assert [x["name"] for x in r] == ["b", "c", "a"] and r[0]["total"] == 7.5
# variant options: re-cut around the drop; a credit only for a known track (never guessed)
e2 = plan.plan_dj_clip(m, 40.0, "c.mp4", "a.wav", cam, tease_bars=0, before_bars=2, after_bars=16, stamp="credit")
assert e2["parts"][0]["audio_in"] == round(107.5 - 2 * bar, 3) and e2["duration"] == round(18 * bar, 3)
assert e2["graphics"] == [] and e2["captions"] == [] and e2["drop_at"] == round(2 * bar, 3)
e3 = plan.plan_dj_clip(m, 40.0, "c.mp4", "a.wav", cam, stamp="credit", track={"title": "Hypnotize", "artist": "X"})
assert e3["graphics"][0]["params"] == {"text": "Hypnotize", "sub": "X"}
from studio import job, build  # noqa: E402
assert job.playing([{"at": 0, "title": "a"}, {"at": 100, "title": "b"}], 107.5)["title"] == "b"
assert job.playing(None, 5) is None
k = build.snap_keys(2.0, 100.0, 30, 10.0)
assert k[0] == (round(2 - 1 / 30, 4), 100.0) and k[1] == (2.0, 107.0) and abs(k[-1][1] - 102.0) < 0.01
print("ok")

# rubric for DJ clips: captions, comment bait and words/s aren't judged (the drop is the hook)
dv = virality.score(e)
assert dv["items"]["captions"]["score"] is None and dv["items"]["comment_trigger"]["score"] is None
print("ok")
