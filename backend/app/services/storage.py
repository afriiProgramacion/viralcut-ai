from pathlib import Path
from ..config import settings
import shutil, uuid, os


def project_dir(pid: str) -> Path:
    p = settings.outputs_dir / pid
    p.mkdir(parents=True, exist_ok=True)
    return p


def clips_dir(pid: str) -> Path:
    p = project_dir(pid) / "clips"
    p.mkdir(parents=True, exist_ok=True)
    return p


def thumbs_dir(pid: str) -> Path:
    p = project_dir(pid) / "thumbs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def temp_dir() -> Path:
    p = settings.temp_dir
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str) -> str:
    import re
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:200]


def save_upload(file, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file, f)
    return dest


def rel_to_data(p: Path) -> str:
    try:
        return str(p.relative_to(settings.data_dir))
    except Exception:
        return str(p)


def abs_from_rel(rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    return settings.data_dir / p


def cleanup_temp(*paths):
    for p in paths:
        try:
            Path(p).unlink(missing_ok=True)
        except Exception:
            pass
