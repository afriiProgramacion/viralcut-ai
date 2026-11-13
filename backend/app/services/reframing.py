import cv2
from pathlib import Path
from ..config import settings
from .video import ffmpeg_path, _run
import subprocess, shutil


def _cascade():
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def detect_face_center(video_path: Path, start: float, end: float) -> tuple[float, float] | None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if w <= 0 or h <= 0:
        cap.release()
        return None
    cascade = _cascade()
    xs, ys = [], []
    t = start
    # sample every 0.5s
    while t < end:
        frame_no = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ok, frame = cap.read()
        if not ok:
            t += 1.0
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(faces) > 0:
            # largest face
            f = max(faces, key=lambda b: b[2] * b[3])
            x, y, fw, fh = f
            xs.append((x + fw / 2) / w)
            ys.append((y + fh / 2) / h)
        t += 1.0
    cap.release()
    if not xs:
        return None
    # median-ish average
    import statistics
    return (statistics.median(xs), statistics.median(ys))


def compute_crop(video_path: Path, start: float, end: float) -> tuple[int, int, int, int]:
    """Return (crop_w, crop_h, x, y) in source pixels for 9:16 output."""
    cap = cv2.VideoCapture(str(video_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if w <= 0 or h <= 0:
        return (0, 0, 0, 0)
    target_aspect = 9 / 16
    src_aspect = w / h
    if src_aspect > target_aspect:
        # wider: crop width
        crop_h = h
        crop_w = int(h * target_aspect)
    else:
        # taller: crop height
        crop_w = w
        crop_h = int(w / target_aspect)
    center = detect_face_center(video_path, start, end)
    if center is None:
        cx, cy = 0.5, 0.5
    else:
        cx, cy = center
    x = int(cx * w - crop_w / 2)
    y = int(cy * h - crop_h / 2)
    x = max(0, min(w - crop_w, x))
    y = max(0, min(h - crop_h, y))
    return (crop_w, crop_h, x, y)


def reframe_clip(src: Path, start: float, end: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    from .video import probe
    info = probe(src)
    dur = max(0.1, end - start)
    crop_w, crop_h, x, y = compute_crop(src, start, end)
    w, h = settings.output_width, settings.output_height
    if crop_w <= 0 or crop_h <= 0:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:
        vf = f"crop={crop_w}:{crop_h}:{x}:{y},scale={w}:{h}"
    cmd = [ffmpeg_path(), "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
           "-vf", vf, "-r", str(settings.target_fps),
           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("reframe failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out
