import cv2
import subprocess
import shutil
import statistics
from pathlib import Path
from ..config import settings


def _cascade():
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def _ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"


def _extract_frame(video_path: Path, t: float, out_path: Path, width: int = 320) -> bool:
    cmd = [_ffmpeg(), "-y", "-ss", f"{t:.2f}", "-i", str(video_path),
           "-vframes", "1", "-vf", f"scale={width}:-1", str(out_path)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.returncode == 0 and out_path.exists()


def detect_face_center(video_path: Path, start: float, end: float) -> tuple[float, float] | None:
    # Sample a few frames via ffmpeg (avoids slow VideoCapture on large files)
    times = [start + (end - start) * f for f in (0.2, 0.5, 0.8)]
    times = [max(start, min(end - 0.5, t)) for t in times]
    xs, ys = [], []
    tmp = Path(settings.temp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    cascade = _cascade()
    for i, t in enumerate(times):
        frame_path = tmp / f"reframe_face_{i}.jpg"
        if not _extract_frame(video_path, t, frame_path, width=320):
            continue
        img = cv2.imread(str(frame_path))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
        if len(faces) > 0:
            f = max(faces, key=lambda b: b[2] * b[3])
            x, y, fw, fh = f
            xs.append((x + fw / 2) / img.shape[1])
            ys.append((y + fh / 2) / img.shape[0])
        try:
            frame_path.unlink(missing_ok=True)
        except Exception:
            pass
    if not xs:
        return None
    return (statistics.median(xs), statistics.median(ys))


def detect_activity_center(video_path: Path, start: float, end: float) -> tuple[float, float] | None:
    # Use two ffmpeg-extracted frames and compute motion
    t1 = max(start, start + (end - start) * 0.3)
    t2 = max(start, start + (end - start) * 0.7)
    tmp = Path(settings.temp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    p1 = tmp / "reframe_act_1.jpg"
    p2 = tmp / "reframe_act_2.jpg"
    if not (_extract_frame(video_path, t1, p1, width=320) and _extract_frame(video_path, t2, p2, width=320)):
        return None
    i1 = cv2.imread(str(p1))
    i2 = cv2.imread(str(p2))
    for pp in (p1, p2):
        try:
            pp.unlink(missing_ok=True)
        except Exception:
            pass
    if i1 is None or i2 is None:
        return None
    g1 = cv2.GaussianBlur(cv2.cvtColor(i1, cv2.COLOR_BGR2GRAY), (21, 21), 0)
    g2 = cv2.GaussianBlur(cv2.cvtColor(i2, cv2.COLOR_BGR2GRAY), (21, 21), 0)
    diff = cv2.absdiff(g1, g2)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None
    x, y, cw, ch = cv2.boundingRect(c)
    return ((x + cw / 2) / i1.shape[1], (y + ch / 2) / i1.shape[0])


def compute_crop(video_path: Path, start: float, end: float, mode: str = "face", zoom: float = 1.0) -> tuple[int, int, int, int]:
    # Get dimensions via ffprobe-like: read one frame
    tmp = Path(settings.temp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    probe_frame = tmp / "reframe_probe.jpg"
    if not _extract_frame(video_path, start, probe_frame, width=640):
        # fallback dimensions
        w, h = 1920, 1080
    else:
        img = cv2.imread(str(probe_frame))
        if img is None:
            w, h = 1920, 1080
        else:
            h, w = img.shape[0], img.shape[1]
        try:
            probe_frame.unlink(missing_ok=True)
        except Exception:
            pass

    target_aspect = 9 / 16
    src_aspect = w / h
    if src_aspect > target_aspect:
        crop_h = h
        crop_w = int(h * target_aspect)
    else:
        crop_w = w
        crop_h = int(w / target_aspect)

    if mode == "face":
        center = detect_face_center(video_path, start, end)
        if center is None:
            center = detect_activity_center(video_path, start, end)
    else:
        center = None
    if center is None:
        cx, cy = 0.5, 0.5
    else:
        cx, cy = center

    zoom = max(1.0, float(zoom))
    crop_w = max(100, int(crop_w / zoom))
    crop_h = max(100, int(crop_h / zoom))
    if crop_w > w:
        crop_w = w
    if crop_h > h:
        crop_h = h

    x = int(cx * w - crop_w / 2)
    y = int(cy * h - crop_h * 0.35)
    x = max(0, min(w - crop_w, x))
    y = max(0, min(h - crop_h, y))
    return (crop_w, crop_h, x, y)


def reframe_clip(src: Path, start: float, end: float, out: Path, mode: str = "face", zoom: float = 1.0) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    from .video import probe
    info = probe(src)
    w_src, h_src = info["width"], info["height"]
    dur = max(0.1, end - start)
    crop_w, crop_h, x, y = compute_crop(src, start, end, mode=mode, zoom=zoom)
    W, H = settings.output_width, settings.output_height
    if crop_w <= 0 or crop_h <= 0:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    else:
        vf = f"crop={crop_w}:{crop_h}:{x}:{y},scale={W}:{H}"
    cmd = [_ffmpeg(), "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
           "-vf", vf, "-r", str(settings.target_fps),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("reframe failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out