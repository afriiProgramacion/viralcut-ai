import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models import Project, Video, Job, Clip
from ..schemas import ProjectCreate, ProjectOut, VideoOut, UploadConfig, YouTubeDownload
from ..services.storage import save_upload, safe_filename, project_dir
import yt_dlp
from ..services.tasks import cancel_task
from ..services.video import probe
from ..config import settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return res.scalars().all()


@router.post("", response_model=ProjectOut)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    p = Project(name=body.name, config=body.config)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.get("/{pid}", response_model=ProjectOut)
async def get_project(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.delete("/{pid}")
async def delete_project(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    # delete files
    import shutil
    d = settings.outputs_dir / pid
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    await db.delete(p)
    await db.commit()
    return {"ok": True}


@router.post("/{pid}/upload", response_model=VideoOut)
async def upload_video(pid: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    # validate size
    max_bytes = settings.max_upload_mb * 1024 * 1024
    # stream to temp then move
    fname = safe_filename(file.filename or "video.mp4")
    dest = settings.uploads_dir / pid / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "File too large")
            f.write(chunk)
    # probe
    try:
        info = probe(dest)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Invalid video: {e}")
    mime = file.content_type or ""
    v = Video(project_id=pid, filename=fname, original_path=str(dest.relative_to(settings.data_dir)),
              size_bytes=size, duration=info["duration"], width=info["width"], height=info["height"], mime=mime)
    db.add(v)
    await db.commit()
    await db.refresh(v)
    p.video_id = v.id
    await db.commit()
    return v


@router.post("/{pid}/start")
async def start_analysis(pid: str, cfg: UploadConfig, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.video_id:
        raise HTTPException(400, "No video uploaded")
    p.config = cfg.model_dump()
    p.status = "processing"
    await db.commit()
    job = Job(project_id=pid, video_id=p.video_id, type="analyze", status="queued", stage="queued", progress=0)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    p.last_job_id = job.id
    await db.commit()
    # launch task
    from ..services.tasks import run_analysis_job
    import asyncio
    asyncio.create_task(run_analysis_job(job.id))
    return {"job_id": job.id}


@router.post("/{pid}/cancel")
async def cancel_project(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    if p.last_job_id:
        cancel_task(p.last_job_id)
        j = await db.get(Job, p.last_job_id)
        if j:
            j.status = "cancelled"
            j.message = "Cancelled by user"
    p.status = "cancelled"
    await db.commit()
    return {"ok": True}


@router.post("/{pid}/reprocess")
async def reprocess_project(pid: str, cfg: UploadConfig, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.video_id:
        raise HTTPException(400, "No video uploaded")
    # cancel running job
    if p.last_job_id:
        cancel_task(p.last_job_id)
        j = await db.get(Job, p.last_job_id)
        if j and j.status in ("queued", "running"):
            j.status = "cancelled"
    # delete existing clips + files
    from sqlalchemy import select as _select
    res = await db.execute(_select(Clip).where(Clip.project_id == pid))
    for c in res.scalars().all():
        if c.file_path:
            try:
                from ..services.storage import abs_from_rel
                abs_from_rel(c.file_path).unlink(missing_ok=True)
            except Exception:
                pass
        if c.thumb_path:
            try:
                from ..services.storage import abs_from_rel
                abs_from_rel(c.thumb_path).unlink(missing_ok=True)
            except Exception:
                pass
        await db.delete(c)
    p.config = cfg.model_dump()
    p.status = "processing"
    await db.commit()
    job = Job(project_id=pid, video_id=p.video_id, type="analyze", status="queued", stage="queued", progress=0)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    p.last_job_id = job.id
    await db.commit()
    from ..services.tasks import run_analysis_job
    import asyncio
    asyncio.create_task(run_analysis_job(job.id))
    return {"job_id": job.id}


@router.post("/youtube")
async def youtube_download(body: YouTubeDownload, db: AsyncSession = Depends(get_db)):
    import asyncio, shutil
    from ..schemas import YouTubeDownload as YTD
    url = body.url.strip()
    if not url:
        raise HTTPException(400, "URL required")
    # create project
    p = Project(name="YouTube video")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    dest_dir = settings.uploads_dir / p.id
    dest_dir.mkdir(parents=True, exist_ok=True)

    def _download():
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(dest_dir / "video.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info

    try:
        info = await asyncio.to_thread(_download)
    except Exception as e:
        await db.delete(p)
        await db.commit()
        raise HTTPException(400, f"Download failed: {e}")

    # find downloaded file
    downloaded = None
    for f in dest_dir.iterdir():
        if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov"):
            downloaded = f
            break
    if not downloaded:
        await db.delete(p)
        await db.commit()
        raise HTTPException(400, "Downloaded file not found")

    fname = safe_filename(downloaded.name)
    if downloaded.name != fname:
        newp = dest_dir / fname
        downloaded.rename(newp)
        downloaded = newp

    try:
        inf = probe(downloaded)
    except Exception as e:
        downloaded.unlink(missing_ok=True)
        await db.delete(p)
        await db.commit()
        raise HTTPException(400, f"Invalid video: {e}")

    v = Video(project_id=p.id, filename=fname,
              original_path=str(downloaded.relative_to(settings.data_dir)),
              size_bytes=downloaded.stat().st_size, duration=inf["duration"],
              width=inf["width"], height=inf["height"], mime="video/mp4")
    db.add(v)
    await db.commit()
    await db.refresh(v)
    p.video_id = v.id
    cfg = body.config.model_dump() if body.config else None
    if cfg:
        p.config = cfg
    p.status = "processing" if cfg else "created"
    await db.commit()

    if cfg:
        job = Job(project_id=p.id, video_id=v.id, type="analyze", status="queued", stage="queued", progress=0)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        p.last_job_id = job.id
        await db.commit()
        from ..services.tasks import run_analysis_job
        asyncio.create_task(run_analysis_job(job.id))
        return {"project_id": p.id, "video_id": v.id, "job_id": job.id, "title": info.get("title")}

    return {"project_id": p.id, "video_id": v.id, "title": info.get("title")}


@router.get("/{pid}/video", response_model=VideoOut)
async def get_video(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p or not p.video_id:
        raise HTTPException(404, "No video")
    v = await db.get(Video, p.video_id)
    return v
