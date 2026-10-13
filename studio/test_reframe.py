"""Reframe on real footage: python -m studio.test_reframe
A talking head pasted far left of a 16:9 canvas for 10 s, then far right (make it with ffmpeg
from any face reel, see the master plan notes). The camera must find it on both sides."""
from pathlib import Path

from studio import plan, reframe

clip = Path(r"E:\AI\studio-jobs\_testmedia\wide_face.mp4")
path = reframe.follow(reframe.faces(clip, 0, 20), plan.crop_fraction(1920, 1080))
left = [c for t, c in path if 1 <= t < 9.5]
right = [c for t, c in path if 11 <= t < 19.5]
print(f"left {min(left):.3f}-{max(left):.3f}  right {min(right):.3f}-{max(right):.3f}")
# the face sits at ~0.20-0.33 (left) and ~0.72-0.85 (right) of the canvas width
assert all(0.17 <= c <= 0.36 for c in left) and all(0.69 <= c <= 0.85 for c in right)
keys = reframe.keyframes(path)
print(len(path), "samples ->", len(keys), "keyframes")
assert len(keys) < len(path) / 3  # a steady camera, not one key per sample
print("ok")
