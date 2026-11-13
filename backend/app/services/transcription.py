import subprocess, shutil
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
from ..config import settings


_model_cache = {}


def _decode_audio_ffmpeg(audio_path: Path, sr: int = 16000) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ffmpeg, "-nostdin", "-threads", "0", "-i", str(audio_path),
           "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg decode failed: " + p.stderr.decode(errors="ignore")[-300:])
    data = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return data


def get_model(size: str | None = None, device: str | None = None, compute_type: str | None = None):
    size = size or settings.whisper_model
    device = device or settings.whisper_device
    compute_type = compute_type or settings.whisper_compute_type
    key = (size, device, compute_type)
    if key not in _model_cache:
        _model_cache[key] = WhisperModel(size, device=device, compute_type=compute_type)
    return _model_cache[key]


def transcribe(audio_path: Path, language: str = "auto", model_size: str | None = None,
              device: str | None = None, compute_type: str | None = None) -> dict:
    model = get_model(model_size, device, compute_type)
    audio = _decode_audio_ffmpeg(Path(audio_path), 16000)
    lang = None if language in ("auto", "", None) else language
    segments, info = model.transcribe(
        audio,
        language=lang,
        word_timestamps=True,
        vad_filter=True,
        beam_size=1,
        condition_on_previous_text=False,
    )
    segs = []
    words = []
    full_text_parts = []
    for seg in segments:
        segs.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
        full_text_parts.append(seg.text.strip())
        if seg.words:
            for w in seg.words:
                words.append({"start": float(w.start), "end": float(w.end), "word": w.word.strip(),
                              "prob": float(w.probability)})
    return {
        "language": getattr(info, "language", language),
        "full_text": " ".join(full_text_parts).strip(),
        "segments": segs,
        "words": words,
    }
