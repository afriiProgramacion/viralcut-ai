import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models import Project, Video, Job
from ..schemas import ProjectCreate, ProjectOut, VideoOut, UploadConfig
from ..services.storage import save_upload, safe_filename, project_dir
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


@router.get("/{pid}/video", response_model=VideoOut)
async def get_video(pid: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(Project, pid)
    if not p or not p.video_id:
        raise HTTPException(404, "No video")
    v = await db.get(Video, p.video_id)
    return v
