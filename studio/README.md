# Creative Studio orchestrator

Python layer of the Creative Studio (master plan: vault `Creative Studio/Master plan.md`; research: `Creative Studio/Research - open-source AI video editors.md`). It turns raw footage into edits by driving FilmCraft through its command protocol only (MCP stdio session, `fc.py`), so upstream FilmCraft updates don't break it.

This folder lives in the fork but touches no upstream file. Upstream merges never conflict with it.

**How things should look** lives in [`direction/`](direction/CLAUDE.md): the never-ship list, measured motion values, the review gates, per-identity packs (`house`, `club`), job briefs and the graphics library. Read it before changing any template.

## Talking-head (P1)

```
python -m studio.job talking-head <video>            # -> E:/AI/studio-jobs/<name>/ (versioned)
python -m studio.test_studio                          # self-checks (pure logic)
python -m studio.make_raw_test <video> <words.json> <out.mp4>   # synthetic raw take for testing
```

Pipeline:
1. `analyze.words`: Whisper `small.en` on the CPU, word timestamps, cached.
2. `analyze.speech_segments`: drops silences > 0.35 s and filler words; pads 80 ms.
3. `plan.plan_talking_head`: builds the EDL v1.
   - segments laid back to back, alternating 112% punch-ins
   - word-grouped captions (≤3 words), frame-snapped
4. `build.build`: compiles the EDL into a FilmCraft project with commands (`timeline.place`, `effects.setParam motion.scale`, `captions.*`).
5. `build.export`: H.264, burned captions, CPU rendering.

Each run writes `edl.vN.json`, `project.vN.fcproj`, `render.vN.mp4` and `report.vN.json`. Nothing is overwritten.

## FilmCraft gotchas found
- Caption times must be frame-exact ticks (`time = frame * TICKS // fps`). Seconds like 4.8333 land a hair inside the previous caption and fail with "a caption already covers this time".
- `file.import` returns `{"items": [ids]}` and `timeline.place` returns `{"clips": [video, audio]}`.
- Text is positioned by its alignment point: set `align: center` to centre it.
- Export with `--gpu-rendering off` while the GPU is unstable under sustained load.

Requirements: the studio venv `E:\AI\filmcraft\.venv` and the FilmCraft 0.7.2 CLI (`FILMCRAFT_CLI` overrides its path). The venv has numpy, faster-whisper, rapidocr-onnxruntime and playwright; playwright drives the Edge that ships with Windows.

## DJ set (P2 core)

```
python -m studio.job dj <camera.mp4> <serato-recording.wav>   # -> the filmed drops as clips
python -m studio.test_dj                                       # synthetic-techno ground truth
```

1. `dj.sync_offset` aligns the camera's room-mic audio with the clean recording.
   - Coarse: onset envelopes.
   - Fine: raw waveform within ±0.3 s.
   - Confidence is a z-score, because techno repeats every beat.
   - Synthetic test: exact to 5 ms, confidence 15–21.
2. `dj.find_drops` finds where the bass returns after a breakdown: the contrast of the mean low-band level 8 s before vs 3 s after, pinned to the first kick back. Synthetic set: 6/6 drops within 0.55 s.
3. `dj.moments`: each drop with 4 bars of build-up and 8 bars of payoff, on the local bar grid (BPM from onset autocorrelation).
4. `build.build_dj`: camera picture (video only) + clean audio (synced to 0.1 ms) + "TRACK ID?" hook, then CPU export.

Not yet: mix transitions, crowd/hands-on moments (vision, needs the GPU), real track IDs (whatstheID).

## Motion graphics (P4, first slice)

`mograph.py` renders HTML animation to transparent PNG frames in headless Edge, frame by frame, then places them as an image sequence on V2/V3 (FilmCraft composites the alpha). This is the "web page as a stop-motion camera" technique (timecut/timeweb, Remotion, HyperFrames, Replit's renderer).
- **Virtual clock:** a script injected before the page's own replaces `Date`, `performance.now`, `requestAnimationFrame` and the timers, so time only moves when a frame is stepped. Canvas, GSAP, Three.js and Lottie land exactly on each frame however slow the screenshot is, and two renders are byte-identical. `OffscreenCanvas` is off, because a worker canvas would dodge the clock.
- **Each frame:** advance the clock (due timers, then one animation frame), seek every CSS/WAAPI animation from when it first appeared, seek paused GSAP timelines on `window.__timelines` (the HyperFrames contract), and call `window.seek(t)` if the page defines it.
- **Measured:** before the clock, a rAF-driven ball ran ~1.4× too fast (wall-clock time while each screenshot took ~100 ms). Now it's within 1 px; a GSAP ticker tween and a `__timelines` timeline are both exact. Check: `python -m studio.test_mograph`.
- Built-in templates: `kinetic-title`, `lower-third`, `track-id`.
- An EDL `"graphics"` entry can name a template or carry its own `"html"` (for LLM/Claude-written graphics). The contract: CSS animations or `window.seek(seconds)`, with a transparent background.
- DJ clips use `track-id`, which slams in exactly on the drop.

## Reframe (wide footage -> 9:16)

`reframe.py` replaces the blind centre crop for any source wider than 9:16.
- YuNet (built into OpenCV 5; model `E:\AI\filmcraft\models\face_detection_yunet_2023mar.onnx`, from opencv_zoo) finds the biggest face every 0.25 s.
- A virtual camera follows it: deadzone 15% of the crop, eased catch-up, a hard cut when the subject jumps, hold when the face is lost. These are opensource-clipping's rules.
- Talking-head: one steady position per segment, since jump cuts hide the reposition. DJ clips: keyframed `motion.position`, with a hold key before each cut so FilmCraft doesn't turn it into a whip pan.
- `motion.position` is where the source's centre lands in the frame (sequence pixels). `position_x` clamps it so no edge shows.
- Check: `python -m studio.test_reframe` (a face pasted left, then right, of a 16:9 canvas).

## Post-render QA

`qa.check(render, edl, seconds)` runs on every render and lands in the report as `"qa": {"ok", "problems", ...}`. It's OpenMontage's self-review idea.
- **ffprobe:** size, fps, audio stream, and length against the EDL (±2 frames).
- **One ffmpeg pass:** black ≥ 0.5 s, frozen picture ≥ 2 s, silence ≥ 1.5 s, true peak > −1 dBTP.
- **Captions:** a bottom anchor must clear Instagram's caption/buttons overlay (≥ 20% margin).

It found two real bugs on its first run:
- The export's `"loudnessLufs"` key was silently ignored, because `--settings` is `ExportSettings` JSON. The export now sets `effects.loudness` with a −2.5 dBTP ceiling (the AAC encode overshoots the limiter by ~1 dB). Result: −14.1 LUFS, −2.3 dBTP.
- Bottom captions sat under the Reels UI. Style packs now use a 0.24 bottom margin.

## DJ hook: flash-forward tease

DJ clips used to open on 4 bars of build-up, so the drop only hit around 7 s in. Every retention source puts the payoff in the first 1.5 s.
- `plan.plan_dj_clip(..., tease_bars=1)` now opens on one bar of the drop, then cuts back to the build-up. Both cuts sit on bar lines.
- The EDL is a list of `parts` (camera picture + clean audio each). `build_dj` places them, and keyframe `time` is sequence time (FilmCraft converts it with `source_time_at`).
- The rubric's hook item for DJ clips is now "does the drop land within 1.5 s" (`drop_at`).
- Verified on the synthetic set: each part's audio matches the recording within 0.1 ms (correlation ≥ 0.98).
- `tease_bars=0` gives the old straight clip.

## Upstream sync

`sh studio/verify_sync.sh` runs the self-checks, a talking-head job and a DJ job against the pinned FilmCraft and prints each render's QA. Run it after merging an upstream tag and moving `fc.CLI` to that release's portable build.
- **2026-10-13: 0.6.0 → 0.7.2 (382 commits).** The command changes we use were all additive: `file.newSequence` `fromItems`, `timeline.place` `items`, keyframe `time` kept outside the clip, FLAC/EXR export options, and 7 new commands. Results matched 0.6.0.

## AI director: planner + judge (`llm.py`, `director.py`)

`llm.ask(prompt, schema, images, provider)` is the single entry point. Each call is recorded in the report with its provider and model.
- **`local`:** Ollama (`coder-stable` for text, `qwen3-vl:8b` for images) under `gpu.lock`, with `yield_to_music=True`, so it waits while Serato DJ Pro or Ableton Live is open.
- **`claude`:** `claude -p --json-schema`, run on the owner's subscription. The CLI must be logged in (`claude` → `/login`).
- **`rules`:** no LLM at all.
- `STUDIO_LLM` (or `--llm`) picks the provider.

DJ job: `python -m studio.job dj <camera> <recording> [--llm rules|local|claude]`.
- Detected drops go to the planner, which picks moments and designs 3 variants of each. Every choice comes from a menu the builder can execute: tease 0/1/2 bars, 2/4/8 bars before the drop, 4/8/16 after, a hook caption of ≤ 5 words, and the drop stamp.
- Each variant is built, exported, QA'd and scored by the rubric.
- A contact sheet goes to the LLM judge, which scores hook, payoff/loop and visual, and suggests one fix.
- The ranking combines the rubric and the judge, half each; QA failures go last.
- If the LLM fails, the job falls back to the rules plan and records the reason.

## Sync and tempo on real music (`test_sync.py`)

Benchmark: a public Boiler Room set, with the camera simulated as a phone mic (high-pass, low-pass, room reverb, AGC, noise).
- **Coarse:** loudness at 20 Hz matched by Pearson correlation. Beat-level envelopes repeat every bar, and raw correlation favours the loudest stretch.
- **Overlap:** the camera must lie at least 90% inside the recording. Edge overlaps spiked.
- **Fine:** GCC-PHAT on the raw waveform, ±1.5 s around the coarse estimate.
- **Confidence:** peak-to-sidelobe ratio. True matches score 24–122, other recordings ≤ 5, and pure synthetic loops about 11; the gate is 15.
- **Result:** 10/10 sample-exact, in a normal room and a very wet one.
- **Tempo:** the onset envelope runs at 11025/55 = 200.45 Hz, not 200. Range 115–165 BPM, with sub-sample refinement of the bar lag (8-bar drift ≤ 8 ms). Each drop is read 3 times; if the reads disagree by more than 1.5 BPM, the set tempo is used and `bpm_sure` is false.
- **Drops:** the bass must stay back (median of the after-window), and the local level has a floor of ¼ of the set's median. Without it, a lone boom in the intro ranked first.

## Motion-graphics videos (`promo.py`)

`python -m studio.job promo "<brief>" [--seconds 20] [--music bed.m4a] [--llm ...]`, or `promo - --storyboard board.json`.
- **Flow:** storyboard (LLM, or a file) → one HTML page with every scene on one CSS timeline → frame-exact render → H.264. Music gets fades and −14 LUFS.
- **Scene types:** title, words, list, stat (a count-up via `@property`), image (Ken Burns), cta.
- **Motion (animate skill):** transform, opacity and clip-path only; strong ease-out entrances, ease-in-out exits, 0.95 + fade (never scale 0).
- **Text fit:** measured on resting layout boxes. Entrance poses and glyph ink beyond the line box would otherwise read as overflow.
- **Capture:** JPEG for opaque videos, 3× faster than PNG (16.5 s of video renders in ~70 s).
