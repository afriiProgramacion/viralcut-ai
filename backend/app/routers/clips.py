import io, zipfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models import Clip, Project
from ..schemas import ClipOut, ClipEdit
from ..config import settings
from ..services.storage import abs_from_rel

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.get("", response_model=list[ClipOut])
async def list_clips(project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Clip).order_by(Clip.created_at.desc())
    if project_id:
        q = q.where(Clip.project_id == project_id)
    res = await db.execute(q)
    return res.scalars().all()


@router.get("/{cid}", response_model=ClipOut)
async def get_clip(cid: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Clip, cid)
    if not c:
        raise HTTPException(404, "Clip not found")
    return c


@router.patch("/{cid}", response_model=ClipOut)
async def edit_clip(cid: str, body: ClipEdit, db: AsyncSession = Depends(get_db)):
    c = await db.get(Clip, cid)
    if not c:
        raise HTTPException(404, "Clip not found")
    if body.start is not None:
        c.start = body.start
    if body.end is not None:
        c.end = body.end
    if body.start is not None or body.end is not None:
        c.duration = c.end - c.start
    if body.title is not None:
        c.title = body.title
    if body.subtitle_style is not None:
        c.subtitle_style = body.subtitle_style
    if body.subtitles is not None:
        c.subtitles = body.subtitles
    c.status = "edited"
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/{cid}")
async def delete_clip(cid: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Clip, cid)
    if not c:
        raise HTTPException(404, "Clip not found")
    if c.file_path:
        try:
            abs_from_rel(c.file_path).unlink(missing_ok=True)
        except Exception:
            pass
    await db.delete(c)
    await db.commit()
    return {"ok": True}


@router.get("/{cid}/file")
async def download_clip(cid: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Clip, cid)
    if not c or not c.file_path:
        raise HTTPException(404, "File not found")
    p = abs_from_rel(c.file_path)
    if not p.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(str(p), media_type="video/mp4", filename=f"{c.title or 'clip'}.mp4")


@router.get("/{cid}/thumb")
async def thumb(cid: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Clip, cid)
    if not c or not c.thumb_path:
        raise HTTPException(404, "Thumb not found")
    p = abs_from_rel(c.thumb_path)
    if not p.exists():
        raise HTTPException(404, "Thumb missing")
    return FileResponse(str(p), media_type="image/jpeg")


@router.post("/{cid}/export")
async def export_clip(cid: str, reframe_mode: str = "face", zoom: float = 1.0, db: AsyncSession = Depends(get_db)):
    # re-burn with current subtitles/style and trim
    c = await db.get(Clip, cid)
    if not c:
        raise HTTPException(404, "Clip not found")
    from ..services import video as V
    from ..services.storage import abs_from_rel, temp_dir
    src_video = None
    # find original video
    from ..models import Video
    v = await db.get(Video, c.video_id)
    orig = abs_from_rel(v.original_path)
    out = abs_from_rel(c.file_path) if c.file_path else None
    if out is None:
        out = settings.outputs_dir / c.project_id / "clips" / f"{cid}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
    # trim + reframe
    V.reframe_clip(orig, c.start, c.end, out) if False else None
    from ..services.reframing import reframe_clip
    reframe_clip(orig, c.start, c.end, out, mode=reframe_mode, zoom=zoom)
    # burn subs
    if c.subtitles:
        try:
            from ..services import video as V2
            srt = temp_dir() / f"{cid}.srt"
            V2.make_srt(c.subtitles, srt)
            burned = out.with_name(out.stem + "_b.mp4")
            V2.burn_subtitles(out, srt, burned, style=c.subtitle_style)
            burned.replace(out)
        except Exception:
            pass
    c.file_path = str(out.relative_to(settings.data_dir))
    c.status = "exported"
    await db.commit()
    return {"file_path": c.file_path}


@router.get("/project/{pid}/zip")
async def download_zip(pid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clip).where(Clip.project_id == pid))
    clips = res.scalars().all()
    if not clips:
        raise HTTPException(404, "No clips")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for c in clips:
            if not c.file_path:
                continue
            p = abs_from_rel(c.file_path)
            if p.exists():
                z.write(p, arcname=f"{c.title or c.id}.mp4")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                            headers={"Content-Disposition": f"attachment; filename=clips_{pid}.zip"})
