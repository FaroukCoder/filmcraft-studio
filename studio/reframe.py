"""Subject-tracking 9:16 reframe (master plan ①). A blind centre crop of a wide camera cuts the
DJ or speaker out whenever they stand off-centre, so: find the face in sampled frames (YuNet,
built into OpenCV), move a virtual camera like an operator would, and turn it into FilmCraft
`motion.position` values (static per talking-head segment, keyframed for a DJ clip).

The camera rules follow opensource-clipping (NaufalRizqullah/opensource-clipping): sample every
0.25 s, ignore weak detections, a deadzone so the camera doesn't drift with every head turn,
eased catch-up, and a hard cut when the subject jumps (a scene cut or a different person)."""
from __future__ import annotations

from pathlib import Path

MODEL = Path(r"E:\AI\filmcraft\models\face_detection_yunet_2023mar.onnx")  # opencv_zoo, 230 KB
STEP, MIN_CONF = 0.25, 0.6
DEADZONE, EASE, SNAP = 0.15, 0.3, 0.35  # deadzone: share of the crop width; snap: of the source


def faces(video: Path, start: float, end: float, step: float = STEP) -> list[tuple[float, float | None]]:
    """[(t, face centre x as a fraction of the source width, or None)] every `step` s.
    ponytail: the biggest face is "the subject"; crowd shots may need a person/motion prior."""
    import cv2
    cap = cv2.VideoCapture(str(video))
    det, out, t = None, [], start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        k = 640 / frame.shape[1]  # detect on a 640 px wide copy: fast, and big enough for a face
        small = cv2.resize(frame, None, fx=k, fy=k)
        if det is None:
            det = cv2.FaceDetectorYN.create(str(MODEL), "", (small.shape[1], small.shape[0]), MIN_CONF)
        _, found = det.detect(small)
        if found is None or not len(found):
            out.append((round(t, 3), None))
        else:
            x, _, w, h = max(found, key=lambda f: f[2] * f[3])[:4]
            out.append((round(t, 3), float((x + w / 2) / small.shape[1])))
        t += step
    cap.release()
    return out


def follow(samples: list[tuple[float, float | None]], crop: float) -> list[tuple[float, float]]:
    """Virtual camera centre (fraction of the source width) per sample. `crop` = crop width /
    source width. No face yet -> centre; a lost face -> hold. Clamped so the crop stays inside."""
    lo, hi = crop / 2, 1 - crop / 2
    cam, out = None, []
    for t, x in samples:
        if x is not None:
            if cam is None or abs(x - cam) > SNAP:
                cam = x  # first sight, or the subject jumped: cut, don't pan across the room
            elif abs(x - cam) > DEADZONE * crop:
                cam += EASE * (x - cam)
            cam = min(max(cam, lo), hi)
        out.append((t, cam))
    first = next((c for _, c in out if c is not None), 0.5)
    return [(t, round(first if c is None else c, 4)) for t, c in out]


def position_x(cam: float, src_w: int, scale: float, out_w: int = 1080) -> float:
    """FilmCraft `motion.position` x (the source centre's place in the frame, in sequence
    pixels) that puts source point `cam` in the middle, never showing past the source edge."""
    wide = src_w * scale / 100
    off = (0.5 - cam) * wide
    limit = max(0.0, (wide - out_w) / 2)
    return round(out_w / 2 + min(max(off, -limit), limit), 1)


def keyframes(path: list[tuple[float, float]], min_move: float = 0.005) -> list[tuple[float, float]]:
    """Only the samples where the camera moves; a hard cut gets a hold key just before it, so
    FilmCraft's interpolation doesn't turn the cut into a whip pan."""
    keys: list[tuple[float, float]] = []
    for t, c in path:
        if not keys:
            keys.append((t, c))
        elif abs(c - keys[-1][1]) >= min_move:
            if abs(c - keys[-1][1]) > SNAP / 2 and t - 1 / 30 > keys[-1][0]:
                keys.append((round(t - 1 / 30, 4), keys[-1][1]))
            keys.append((t, c))
    return keys


def segment_centres(video: Path, spans: list[tuple[float, float]], crop: float) -> list[float]:
    """One steady camera position per talking-head segment (jump cuts hide the reposition)."""
    out = []
    for a, b in spans:
        path = follow(faces(video, a, max(b, a + STEP)), crop)
        xs = sorted(c for _, c in path)
        out.append(xs[len(xs) // 2] if xs else 0.5)
    return out
