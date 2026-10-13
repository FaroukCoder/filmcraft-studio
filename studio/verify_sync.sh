#!/bin/sh
# Upstream-sync check: self-checks + one talking-head and one DJ job on the pinned FilmCraft.
cd /e/AI/filmcraft/filmcraft-studio || exit 1
PY=../.venv/Scripts/python.exe
export PYTHONIOENCODING=utf-8
$PY -m studio.test_studio && $PY -m studio.test_reframe 2>&1 | grep -v WARN && $PY -m studio.test_dj 2>&1 | tail -2 || exit 1
$PY -m studio.job talking-head /e/AI/studio-jobs/_testmedia/wide_talk.mp4 2>&1 | grep -v WARN > /e/AI/studio-jobs/_probe/sync_th.json
$PY -m studio.job dj /e/AI/studio-jobs/_testmedia/set_camera.mp4 /e/AI/studio-jobs/_testmedia/set_clean.wav 2>&1 | grep -v WARN > /e/AI/studio-jobs/_probe/sync_dj.json
$PY - <<'P'
import json
th = json.load(open(r"E:\AI\studio-jobs\_probe\sync_th.json"))
dj = json.load(open(r"E:\AI\studio-jobs\_probe\sync_dj.json"))
print("talking-head", th["version"], th["edited_seconds"], "s, cuts", th["cuts"], "virality", th["virality"]["total"], "qa", th["qa"]["ok"], th["qa"]["problems"], th["qa"]["true_peak"])
for c in dj["clips"]:
    print("dj", c["render"].split("\\")[-1], "virality", c["virality"], "qa", c["qa"]["ok"], c["qa"]["problems"])
P
