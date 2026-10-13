# Creative Studio orchestrator

Python layer of the Creative Studio (master plan: vault `Plans/Creative Studio - master plan.md`). It turns raw footage into edits by driving FilmCraft through its command protocol only (MCP stdio session, `fc.py`), so upstream FilmCraft updates don't break it.

This folder lives in the fork but touches no upstream file. Upstream merges never conflict with it.

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

Requirements: the studio venv `E:\AI\filmcraft\.venv` and the FilmCraft 0.6.0 CLI (`FILMCRAFT_CLI` overrides its path). The venv has numpy, faster-whisper, rapidocr-onnxruntime and playwright; playwright drives the Edge that ships with Windows.

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

`mograph.py` renders HTML/CSS animation to transparent PNG frames in headless Edge, stepping the page's animations frame by frame so renders are exact. Then it places them as an image sequence on V2/V3 (FilmCraft composites the alpha).
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
