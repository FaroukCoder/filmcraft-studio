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

Requirements for now: the `E:\AI\reels\.venv` interpreter (faster-whisper, numpy) and the FilmCraft 0.6.0 CLI (`FILMCRAFT_CLI` overrides its path).

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
