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
