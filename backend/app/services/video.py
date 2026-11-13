import json, subprocess, os, shutil
from pathlib import Path
from ..config import settings


def _run(cmd, timeout=600):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


def ffmpeg_path() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_path() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def probe(path: Path) -> dict:
    cmd = [ffprobe_path(), "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]
    r = _run(cmd, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore"))
    data = json.loads(r.stdout.decode())
    fmt = data.get("format", {})
    vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    astream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    duration = float(fmt.get("duration", 0) or vstream.get("duration", 0) or 0)
    width = int(vstream.get("width", 0) or 0)
    height = int(vstream.get("height", 0) or 0)
    return {"duration": duration, "width": width, "height": height,
            "audio_codec": astream.get("codec_name"), "video_codec": vstream.get("codec_name")}


def extract_audio(video_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_path(), "-y", "-i", str(video_path), "-vn",
           "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(out_path)]
    r = _run(cmd, timeout=1200)
    if r.returncode != 0:
        raise RuntimeError("extract_audio failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out_path


def cut_clip(src: Path, start: float, end: float, out: Path, reframe_plan: dict | None = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = max(0.1, end - start)
    # base reframe: center crop to 9:16 if horizontal
    w, h = settings.output_width, settings.output_height
    # We'll do a simple centered crop+scale first; intelligent reframe applied separately if plan
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    cmd = [ffmpeg_path(), "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
           "-vf", vf, "-r", str(settings.target_fps),
           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("cut_clip failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out


def apply_reframe(src: Path, out: Path, crop_x: int, crop_y: int, crop_w: int, crop_h: int) -> Path:
    # crop region from source then scale to output
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h = settings.output_width, settings.output_height
    vf = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={w}:{h}"
    cmd = [ffmpeg_path(), "-y", "-i", str(src), "-vf", vf, "-r", str(settings.target_fps),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("reframe failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out


def normalize_audio(src: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_path(), "-y", "-i", str(src), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("normalize failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out


def thumbnail(video_path: Path, out: Path, at: float = 1.0) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_path(), "-y", "-ss", f"{at:.3f}", "-i", str(video_path),
           "-vframes", "1", "-q:v", "2", str(out)]
    r = _run(cmd, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("thumb failed: " + r.stderr.decode(errors="ignore")[-300:])
    return out


def burn_subtitles(src: Path, srt_path: Path, out: Path, style: str = "hormozi") -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Build force_style based on preset
    styles = {
        "hormozi": "FontName=Arial,FontSize=14,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV=60",
        "mrbeast": "FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=3,Shadow=0,Alignment=2,MarginV=70",
        "minimal": "FontName=Arial,FontSize=12,Bold=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=50",
        "karaoke": "FontName=Arial,FontSize=14,Bold=1,PrimaryColour=&H0000FF00,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV=60",
        "bold_yellow": "FontName=Arial,FontSize=15,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=3,Shadow=0,Alignment=2,MarginV=65",
        "clean_podcast": "FontName=Arial,FontSize=12,Bold=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H00222222,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=40",
    }
    fs = styles.get(style, styles["hormozi"])
    # escape path for ffmpeg subtitles filter
    sp = str(srt_path).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{sp}':force_style='{fs}'"
    cmd = [ffmpeg_path(), "-y", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "copy", "-movflags", "+faststart", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("burn_subtitles failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out


def make_srt(subtitles: list, out: Path) -> Path:
    """subtitles: list of {start,end,text}"""
    out.parent.mkdir(parents=True, exist_ok=True)
    def ts(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines = []
    for i, s in enumerate(subtitles, 1):
        lines.append(str(i))
        lines.append(f"{ts(s['start'])} --> {ts(s['end'])}")
        lines.append(s["text"])
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def concat_clips(clips: list[Path], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.parent / "concat_list.txt"
    lst.write_text("\n".join(f"file '{str(c).replace(chr(92), '/')}'" for c in clips), encoding="utf-8")
    cmd = [ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)]
    r = _run(cmd, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("concat failed: " + r.stderr.decode(errors="ignore")[-500:])
    return out
