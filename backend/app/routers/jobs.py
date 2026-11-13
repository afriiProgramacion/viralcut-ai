from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models import Job
from ..schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{jid}", response_model=JobOut)
async def get_job(jid: str, db: AsyncSession = Depends(get_db)):
    j = await db.get(Job, jid)
    if not j:
        raise HTTPException(404, "Job not found")
    return j


@router.get("", response_model=list[JobOut])
async def list_jobs(project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Job).order_by(Job.created_at.desc())
    if project_id:
        q = q.where(Job.project_id == project_id)
    res = await db.execute(q)
    return res.scalars().all()


@router.post("/{jid}/cancel")
async def cancel_job(jid: str, db: AsyncSession = Depends(get_db)):
    j = await db.get(Job, jid)
    if not j:
        raise HTTPException(404, "Job not found")
    j.status = "cancelled"
    await db.commit()
    return {"ok": True}
