# Prototypes for the first week

Small, standalone Python scripts behind the Top 10 moves in `../projects-research.md`.
Each has a test that builds synthetic input (no GPU, no model downloads) and checks
the result. They were written and tested in a Linux container on 2026-10-14; they
use only cross-platform calls (pathlib, `subprocess` with argument lists, no shell)
and should run on Windows, but **nobody has run them on Windows yet**.

| Script | Top 10 | What it does | Test result (synthetic) |
|---|---|---|---|
| `analyze_reference_clips.py` | #5 | Cuts vs beats/bars/8-bar phrases, shot length in beats, drop position, for a folder of reference clips | 150 BPM clip, 7 known cuts: BPM 150.02, 7/7 cuts, on-beat 85.7 %, on-bar 71.4 %, drop at 16.02 s (true 16.0) |
| `vlm_json_guard.py` | #3 | Downscaled frames, token budget vs `num_ctx`, Qwen's recommended sampling, bounded schema, loop detection, retry, two-pass fallback; Ollama or OpenAI-compatible API | Fake server that loops, then returns invalid JSON: recovered a valid note via the fallback on both APIs; 8 frames at 360×640 ≈ 1.9k tokens vs > 16k at full resolution |
| `serato_set_grid.py` | #7 | Reads Serato 4 `master.sqlite` history; aligns a track you own inside your set recording (offset + stretch ratio) and maps its grid into set time | Track played 3 % fast with its bass cut for a 30 s blend and noise on top: ratio 1.030 (true 1.03), offset 50.015 s (true 50.0) |
| `l1_reframe_path.py` | #9 | L1-optimal (Grundmann et al.) 9:16 crop path from noisy subject positions | 20 s DJ, 15 px jitter, 10 % missed detections: 83.6 % of frames static, 0 direction changes, subject in frame 100 %; an EMA follow: 11.5 % static, 189 direction changes. Solves 600 frames in 0.2 s |
| `dj_guard.py` | #6 | Unloads llama-swap/ComfyUI and stops GPU services while Serato or Ableton runs; `gpu_allowed()` for batch jobs | Stand-in app process: unload called, lock written, cleared after the grace period |
| `laya_eval.py` | #2 | Accuracy per route, confusions, calibration (ECE), confidence gate, and a cheap baseline on the same labels | Router right 41 % at ~0.9 confidence: ECE 0.49 flagged; TF-IDF baseline 100 % on the learnable synthetic routes |
| `llama-swap.example.yaml` | #6 | One exclusive GPU group: agent, small agent, two VLMs, ComfyUI | YAML parses; group members match model ids (not run: llama-swap is a Go binary I couldn't download here) |

## Setup (Windows, PowerShell, one command per line)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
winget install ffmpeg
```

Optional: `pip install beat-this` (pulls PyTorch) to use Beat This instead of librosa in
`analyze_reference_clips.py`; `pip install sentence-transformers` for an
EmbeddingGemma baseline in `laya_eval.py`.

## Run the tests

```powershell
python run_tests.py
```

## Honest limits

- Synthetic tests prove the code does what it says on clean, known input. They do not
  prove it works on your footage, your sets or your routes; the first-week plan in the
  report says what to measure on real data.
- `serato_set_grid.py` reads the Serato 4 schema as the open-source whats-now-playing
  project reads it. Serato 3.x history (`.session` files) is not handled.
- `analyze_reference_clips.py` counts phrases in 8-bar steps from the detected drop,
  because club tracks start a phrase on the drop. If its drop detection is wrong, the
  phrase column is wrong; the beat and bar columns don't depend on it.
