"""Checks serato_writeback.py.

Anchor (always runs): a synthetic techno track at 132.004 BPM with rolling 16th-note bass
under the kicks, hats and claps, first beat at 0.211 s, analysed with a BPM of 132.0 (0.004
off, about whatstheID's error); kicks have a click and a slowly swelling sub body, like a
recorded one. The grid must land within 3 ms of the click at both ends, the BPM within 0.002. A track whose tempo drifts (a vinyl rip, live drums)
must be refused, not gridded.

Write (needs ffmpeg, mutagen and RB2SERATO_TAGS = path to rb2serato's seratotags.py): grid + 3 cues
into MP3, FLAC and WAV copies; the audio bytes must be unchanged, our decoder must read back
what was written, and serato-tools (an independent parser, if installed) must agree for MP3
and FLAC. A mutation that touches the audio must be rejected with the original untouched,
and implausible numbers must be refused before anything is written. Your own Serato work
must survive a write: hand-set cues keep their slots, loops, colour, BPM lock and (for a
cues-only write) the grid are kept, a new cue next to one of yours is skipped, and a tag
holding data this can't re-encode (a Flip entry) is refused rather than rewritten.

    RB2SERATO_TAGS=/path/to/rb2serato/src/rb2serato/seratotags.py python test_serato_writeback.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import serato_writeback as sw  # noqa: E402

SR = 22050


def synth(bpm: float, t0: float, dur: float, seed: int = 1, drift: float = 0.0) -> np.ndarray:
    """Kick on every beat, sidechained 16th-note sub bass, off-beat hats, claps on 2 and 4.
    drift: BPM change per minute (0 = steady)."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    y = rng.normal(0, 0.03, n)
    t = np.arange(int(0.25 * SR)) / SR
    # a real kick: a 2 ms click, then a sub body that swells over ~15 ms (a recorded loop
    # showed the body peaking ~20 ms after the transient; a detector tuned on an instant
    # sine landed 23 ms late on it). The beat is the click.
    click = np.zeros_like(t)
    nc = int(0.002 * SR)
    click[:nc] = rng.normal(0, 1, nc) * 0.6
    body = np.sin(2 * np.pi * (50 + 120 * np.exp(-t * 30)) * t) * np.minimum(1, t / 0.015) * np.exp(-t * 9)
    kick = click + body
    hat = rng.normal(0, 1, int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 90) * 0.25
    clap = rng.normal(0, 1, int(0.12 * SR)) * np.exp(-np.arange(int(0.12 * SR)) / SR * 25) * 0.5
    tb, i = t0, 0
    while tb < dur - 0.3:
        beat = 60.0 / (bpm + drift * tb / 60.0)
        s = int(round(tb * SR))
        y[s:s + kick.size] += kick
        for q in (1, 2, 3):  # rolling bass on the 16ths after the kick (ducked under it)
            sb = int(round((tb + q * beat / 4) * SR))
            nb = min(int(beat / 4 * SR * 0.8), n - sb)
            if nb <= 0:
                continue
            tt = np.arange(nb) / SR
            y[sb:sb + nb] += 0.45 * np.sin(2 * np.pi * 55 * tt) * np.minimum(1, tt * 200) * np.exp(-tt * 12)
        sh = int(round((tb + beat / 2) * SR))
        y[sh:sh + hat.size] += hat
        if i % 4 in (1, 3):
            y[s:s + clap.size] += clap
        tb += beat
        i += 1
    return y / np.abs(y).max()


def anchor_checks(problems: list) -> dict:
    true_bpm, t0, dur = 132.004, 0.211, 180.0
    y = synth(true_bpm, t0, dur)
    r = sw.grid_anchor(y, SR, 132.0)
    P, Pt = 60 / r.get("bpm", 1), 60 / true_bpm
    k_end = int((dur - 1 - t0) / Pt)
    start_err = (r.get("anchor_s", 0) - t0) * 1000
    end_err = (r.get("anchor_s", 0) + k_end * P - (t0 + k_end * Pt)) * 1000
    # the detector marks 20 % of the rise, a fixed ~2 ms after the click starts; `compare`
    # against Serato's own grids calibrates whatever constant remains
    if not r.get("ok") or abs(start_err) > 3 or abs(end_err) > 3 or abs(r["bpm"] - true_bpm) > 0.002:
        problems.append(f"steady track: {r}, start {start_err:+.2f} ms, end {end_err:+.2f} ms")
    rd = sw.grid_anchor(synth(130.0, t0, dur, seed=2, drift=1.0), SR, 131.5)  # +1 BPM per minute
    if rd.get("ok"):
        problems.append(f"drifting track should be refused: {rd}")
    r1 = sw.grid_anchor(y, SR, 132.0, beat_one=2)  # downbeat two beats after the first beat
    if abs(r1.get("anchor_s", 0) - (t0 + 2 * Pt)) > 0.002:
        problems.append(f"beat_one shift: {r1}")
    return {"steady": r, "start_err_ms": round(start_err, 2), "end_err_ms": round(end_err, 2), "drifting": rd}


def write_checks(problems: list, st_path: str) -> dict:
    st = sw.load_seratotags(st_path)
    try:
        import mutagen
        from serato_tools.track_beatgrid import TrackBeatgrid
        from serato_tools.track_cues_v2 import TrackCuesV2
        from serato_tools.track_tagdump import get_serato_tagdata
        have_st = True
    except ImportError:
        have_st = False
    out = {"serato_tools": have_st}
    bpm, anchor = 132.004, 0.21114
    cues = [{"time": 0.211, "label": "start"}, {"time": 58.39, "label": "drop"}, {"time": 101.5, "label": "outro"}]
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sf.write(d / "src.wav", synth(132.004, 0.211, 30.0), SR)
        for ext, args in ((".mp3", ["-c:a", "libmp3lame", "-b:a", "192k"]), (".flac", []), (".wav", [])):
            f = d / f"track{ext}"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "src.wav"), *args, str(f)], check=True)
            before = sw.audio_digest(f)
            sw.write(str(f), st, bpm, anchor, cues, lock=False, backup_dir=d / "backup", snap=False)
            if sw.audio_digest(f) != before:
                problems.append(f"{ext}: audio changed")
            if not (d / "backup" / f.name).exists():
                problems.append(f"{ext}: no backup kept")
            back = sw.read(str(f), st)
            g = back.get("grid", [{}])[0]
            if abs(g.get("bpm", 0) - bpm) > 1e-3 or abs(g.get("position_s", -1) - anchor) > 1e-5:
                problems.append(f"{ext}: grid read back as {back.get('grid')}")
            if [(c["ms"], c["name"]) for c in back.get("cues", [])] != [(211, "start"), (58390, "drop"), (101500, "outro")]:
                problems.append(f"{ext}: cues read back as {back.get('cues')}")
            row = {"grid": g, "cues": len(back.get("cues", []))}
            if have_st and ext in (".mp3", ".flac"):
                if ext == ".mp3":
                    grid, cue2 = TrackBeatgrid(str(f)), TrackCuesV2(str(f))
                else:
                    raw = dict(get_serato_tagdata(mutagen.File(str(f)), decode=True))
                    grid, cue2 = TrackBeatgrid(raw["Serato BeatGrid"]), TrackCuesV2(raw["Serato Markers2"])
                term = grid.entries[-2] if grid.entries else None
                st_cues = [(e.index, e.position, e.name) for e in cue2.entries if type(e).__name__ == "CueEntry"]
                row["serato_tools"] = {"bpm": term.bpm if term else None, "anchor": term.position_s if term else None,
                                       "cues": st_cues}
                if not term or abs(term.bpm - bpm) > 1e-3 or abs(term.position_s - anchor) > 1e-5:
                    problems.append(f"{ext}: serato-tools reads the grid as {grid.entries}")
                if st_cues != [(0, 211, "start"), (1, 58390, "drop"), (2, 101500, "outro")]:
                    problems.append(f"{ext}: serato-tools reads the cues as {st_cues}")
            if ext != ".wav":  # still decodes, same length
                n0 = sf.info(str(d / "src.wav")).frames
                dec = d / "dec.wav"
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(f), str(dec)], check=True)
                if abs(sf.info(str(dec)).frames - n0) > 2 * SR * 0.05:
                    problems.append(f"{ext}: decoded length changed")
            out[ext] = row

        # a write that damages the audio must not reach the original
        f = d / "track.flac"
        orig = f.read_bytes()

        def damage(tmp: str) -> None:
            b = bytearray(Path(tmp).read_bytes())
            b[-100] ^= 0xFF
            Path(tmp).write_bytes(bytes(b))

        try:
            sw.safe_write(f, damage)
            problems.append("damaged audio was accepted")
        except sw.WriteError:
            pass
        if f.read_bytes() != orig or list(d.glob("*.serato-tmp*")):
            problems.append("original changed or temp file left behind after a refused write")

        # an MP3 offset moves grid and cues by the same amount (fresh file: on the first one the
        # shifted cues would land within 250 ms of the existing ones and be skipped, by design)
        f = d / "offset.mp3"
        shutil.copy2(d / "src.wav", d / "offset.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "offset.wav"), "-c:a", "libmp3lame",
                        "-b:a", "192k", str(f)], check=True)
        sw.write(str(f), st, bpm, anchor, cues, offset_ms=26.0, snap=False)
        back = sw.read(str(f), st)
        if abs(back["grid"][0]["position_s"] - (anchor + 0.026)) > 1e-5 or back["cues"][1]["ms"] != 58416:
            problems.append(f"offset not applied: {back}")

        # with a grid known, cues land on it (whatstheID's sit ~25 ms after the kick)
        f = d / "snap.flac"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "src.wav"), str(f)], check=True)
        res = sw.write(str(f), st, bpm, anchor, [{"time": anchor + 128 * 60 / bpm + 0.027, "label": "drop"}], grid=False)
        want = round((anchor + 128 * 60 / bpm) * 1000)
        if sw.read(str(f), st)["cues"][0]["ms"] != want or abs(res["cue_moves"][0]["ms"] + 27.0) > 0.2:
            problems.append(f"snapped write: {sw.read(str(f), st)['cues']} {res['cue_moves']} want {want}")

        # your own Serato work survives: cues stay in their slots, loops, colour, lock and grid stay
        for ext in (".flac", ".mp3"):
            f = d / f"mine{ext}"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "src.wav"), str(f)], check=True)
            mine = st.SeratoMarkers(
                cues=[st.SeratoCue(0, 1000, st.CUE_PALETTE[5], "mine A"), st.SeratoCue(3, 20000, st.CUE_PALETTE[9], "mine B")],
                loops=[st.SeratoLoop(0, 4000, 8000, "my loop")], track_color=(0x99, 0x00, 0xCC), bpm_locked=True)
            pre = {"Serato BeatGrid": st.encode_beatgrid([st.BeatGridMarker(0.5, 0, 131.0)]),
                   "Serato Markers2": st.encode_markers2_id3(mine), "Serato Markers_": st.encode_markers_id3(mine)}
            if ext == ".flac":
                pre.pop("Serato Markers_")
            sw._tag_file(str(f), pre)
            res = sw.write(str(f), st, None, None, [{"time": 1.1, "label": "drop"}, {"time": 30.0, "label": "intro end"},
                                                     {"time": 60.0, "label": "outro"}], grid=False)
            back = sw.read(str(f), st)
            want = [(0, 1000, "mine A"), (1, 30000, "intro end"), (2, 60000, "outro"), (3, 20000, "mine B")]
            if [(c["slot"], c["ms"], c["name"]) for c in back["cues"]] != want:
                problems.append(f"{ext} merge: cues {back['cues']}")
            if len(res["cues_skipped"]) != 1 or back["loops"] != [{"slot": 0, "start_ms": 4000, "end_ms": 8000}]:
                problems.append(f"{ext} merge: skipped {res['cues_skipped']}, loops {back['loops']}")
            if back["track_color"] != [0x99, 0x00, 0xCC] or not back["bpm_locked"]:
                problems.append(f"{ext} merge: colour/lock lost {back}")
            if abs(back["grid"][0]["bpm"] - 131.0) > 1e-4 or abs(back["grid"][0]["position_s"] - 0.5) > 1e-6:
                problems.append(f"{ext} cues-only write touched the grid: {back['grid']}")
            out[f"merge{ext}"] = {"cues": back["cues"], "skipped": res["cues_skipped"]}

        # Serato data this can't re-encode (a Flip entry) is never rewritten
        def entry(name: bytes, data: bytes) -> bytes:
            return name + b"\x00" + len(data).to_bytes(4, "big") + data
        inner = b"\x01\x01" + entry(b"COLOR", b"\x00\xff\xff\xff") + entry(b"FLIP", b"\x00" * 12) + b"\x00"
        flip = b"\x01\x01" + sw.base64.b64encode(inner).rstrip(b"=") + b"\x00" * 8
        f = d / "flip.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "src.wav"), str(f)], check=True)
        sw._tag_file(str(f), {"Serato Markers2": flip})
        before = f.read_bytes()
        try:
            sw.write(str(f), st, None, None, [{"time": 30.0, "label": "x"}], grid=False)
            problems.append("a Markers2 tag with a FLIP entry was rewritten")
        except sw.WriteError as e:
            out["flip_refused"] = str(e)
        if f.read_bytes() != before:
            problems.append("refused write still changed the file")

        for bad in ((float("nan"), 0.2), (0.0, 0.2), (1000.0, 0.2), (132.0, -1.0), (132.0, float("inf"))):
            try:
                sw.payloads(st, *bad)
                problems.append(f"accepted {bad}")
            except ValueError:
                pass
    return out


def main() -> int:
    problems: list[str] = []
    rep = {"anchor": anchor_checks(problems)}
    st_path = os.environ.get("RB2SERATO_TAGS")
    note = ""
    try:
        import mutagen  # noqa: F401  (GPL-2.0+, optional: only the write path needs it)
        have_mutagen = True
    except ImportError:
        have_mutagen = False
    if st_path and Path(st_path).is_file() and shutil.which("ffmpeg") and have_mutagen:
        rep["write"] = write_checks(problems, st_path)
    else:
        note = " (anchor only; the write checks need ffmpeg, mutagen and RB2SERATO_TAGS)"
    # whatstheID's cues sit ~25 ms after the kick; snapping puts them on the grid, and leaves a
    # cue that isn't near any grid line where it was
    snapped, moves = sw.snap_cues([{"time": 13.47, "label": "drop"}, {"time": 20.36, "label": "odd"}], 0.0032, 125.0)
    if abs(snapped[0]["time"] - 13.4432) > 1e-4 or snapped[1]["time"] != 20.36 or "kept" not in moves[1]:
        problems.append(f"snap_cues: {snapped} {moves}")
    rep["snap"] = moves
    rep["compare"] = sw.compare({"a": {"bpm": 132, "anchor_s": 0.215}, "b": {"bpm": 132, "anchor_s": 0.66955}},
                                {"a": {"bpm": 132, "anchor_s": 0.211}, "b": {"bpm": 132, "anchor_s": 0.211}})
    if [r["error_ms"] for r in rep["compare"]["rows"]] != [4.0, 4.0]:
        problems.append(f"compare: {rep['compare']}")
    print(rep)
    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS" + note)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
