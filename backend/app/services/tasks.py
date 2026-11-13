import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import SessionLocal
from ..models import Job, Video, Transcription, Clip, Project
from ..services import video as V
from ..services.storage import clips_dir, thumbs_dir, temp_dir, abs_from_rel
from ..services.reframing import reframe_clip
from ..services.transcription import transcribe
from ..services.analysis import analyze as analyze_llm

async def _set_job(job_id, **kw):
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        if job:
            for k, v in kw.items():
                setattr(job, k, v)
            job.updated_at = datetime.utcnow()
            await db.commit()


async def _load_cfg(db: AsyncSession) -> dict:
    from ..models import Setting
    res = await db.execute(select(Setting))
    rows = res.scalars().all()
    cfg = {}
    for r in rows:
        cfg[r.key] = r.value
    # map keys
    cfg.setdefault("anthropic_api_key", cfg.get("anthropic_api_key", settings.anthropic_api_key))
    cfg.setdefault("openai_api_key", cfg.get("openai_api_key", settings.openai_api_key))
    cfg.setdefault("ai_provider", cfg.get("ai_provider", settings.ai_provider))
    cfg.setdefault("ai_model", cfg.get("ai_model", settings.ai_model))
    cfg.setdefault("whisper_model", cfg.get("whisper_model", settings.whisper_model))
    cfg.setdefault("whisper_device", cfg.get("whisper_device", settings.whisper_device))
    cfg.setdefault("whisper_compute_type", cfg.get("whisper_compute_type", settings.whisper_compute_type))
    return cfg


def _cfg_from_env():
    return {
        "anthropic_api_key": settings.anthropic_api_key,
        "openai_api_key": settings.openai_api_key,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "whisper_model": settings.whisper_model,
        "whisper_device": settings.whisper_device,
        "whisper_compute_type": settings.whisper_compute_type,
    }


async def run_analysis_job(job_id: str):
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        if not job:
            return
        project_id = job.project_id
        video_id = job.video_id
        cfg_db = await _load_cfg(db)
        # parse config from project
        project = await db.get(Project, project_id) if project_id else None
        proj_config = (project.config if project else None) or {}
    cfg = {**_cfg_from_env(), **cfg_db}
    # override with project config ai? none
    clip_count = int(proj_config.get("clip_count", 5))
    clip_duration = int(proj_config.get("clip_duration", 30))
    platform = proj_config.get("platform", "tiktok")
    priority = proj_config.get("priority", "mixed")
    cut_aggr = proj_config.get("cut_aggressiveness", "balanced")
    language = proj_config.get("language", "auto")
    subtitle_style = proj_config.get("subtitle_style", "hormozi")

    video_path = None
    async with SessionLocal() as db:
        video = await db.get(Video, video_id)
        video_path = Path(video.original_path)
        if not Path(video_path).is_absolute():
            video_path = settings.data_dir / video_path

    try:
        await _set_job(job_id, status="running", stage="Extracting audio", progress=5, message="Extracting audio")
        audio_path = temp_dir() / f"{video_id}.wav"
        V.extract_audio(video_path, audio_path)

        await _set_job(job_id, stage="Transcribing", progress=15, message="Transcribing conversation")
        tcfg = cfg
        tr = transcribe(audio_path, language=language, model_size=tcfg.get("whisper_model"),
                        device=tcfg.get("whisper_device"), compute_type=tcfg.get("whisper_compute_type"))
        # save transcription
        async with SessionLocal() as db:
            existing = (await db.execute(select(Transcription).where(Transcription.video_id == video_id))).scalars().first()
            if existing:
                existing.language = tr["language"]
                existing.full_text = tr["full_text"]
                existing.segments = tr["segments"]
                existing.words = tr["words"]
            else:
                db.add(Transcription(video_id=video_id, language=tr["language"], full_text=tr["full_text"],
                                     segments=tr["segments"], words=tr["words"]))
            await db.commit()

        await _set_job(job_id, stage="Analyzing content", progress=35, message="Analyzing content")
        # duration
        async with SessionLocal() as db:
            video = await db.get(Video, video_id)
            duration = video.duration
        candidates = await analyze_llm(cfg, duration, tr["segments"], clip_count, clip_duration, platform, priority, cut_aggr)

        await _set_job(job_id, stage="Detecting moments", progress=50, message=f"Found {len(candidates)} moments")

        # Generate clips
        cdir = clips_dir(project_id)
        tdir = thumbs_dir(project_id)
        clip_ids = []
        total = max(1, len(candidates))
        for idx, c in enumerate(candidates):
            await _set_job(job_id, stage="Generating clips", progress=50 + int(35 * idx / total),
                           message=f"Generating clip {idx+1}/{total}")
            out_path = cdir / f"clip_{idx+1:02d}.mp4"
            # reframe + cut
            reframe_clip(video_path, c["start"], c["end"], out_path)
            # thumbnail
            thumb_path = tdir / f"clip_{idx+1:02d}.jpg"
            try:
                V.thumbnail(out_path, thumb_path, at=1.0)
            except Exception:
                pass
            # subtitles words
            words = [w for w in tr["words"] if w["start"] >= c["start"] - 0.1 and w["end"] <= c["end"] + 0.1]
            subs = _group_words(words, c["start"])
            # burn subtitles into a separate exported file? We'll keep base clip reframed and store subs.
            # Burn default style for final clip file
            try:
                srt = temp_dir() / f"{project_id}_clip{idx+1}.srt"
                V.make_srt(subs, srt)
                burned = cdir / f"clip_{idx+1:02d}_sub.mp4"
                V.burn_subtitles(out_path, srt, burned, style=subtitle_style)
                # replace base with burned
                out_path.unlink(missing_ok=True)
                burned.rename(out_path)
            except Exception as e:
                # keep base without subs
                pass
            # create clip record
            async with SessionLocal() as db:
                clip = Clip(
                    project_id=project_id,
                    video_id=video_id,
                    start=c["start"],
                    end=c["end"],
                    duration=c.get("duration", c["end"] - c["start"]),
                    title=c.get("title", "Clip"),
                    titles=c.get("titles", []),
                    description=c.get("description", ""),
                    hashtags=c.get("hashtags", []),
                    hook=c.get("hook", ""),
                    category=c.get("category", "mixed"),
                    viral_score=int(c.get("viral_score", 0)),
                    score_breakdown=c.get("score_breakdown", {}),
                    explanation=c.get("explanation", ""),
                    subtitle_style=subtitle_style,
                    subtitles=subs,
                    file_path=V.storage_rel(out_path) if False else str(out_path.relative_to(settings.data_dir)),
                    thumb_path=str(thumb_path.relative_to(settings.data_dir)) if thumb_path.exists() else None,
                )
                db.add(clip)
                await db.commit()
                await db.refresh(clip)
                clip_ids.append(clip.id)

        await _set_job(job_id, stage="Preparing exports", progress=90, message="Finalizing")
        # update project status
        async with SessionLocal() as db:
            if project_id:
                p = await db.get(Project, project_id)
                if p:
                    p.status = "done"
                    await db.commit()
        await _set_job(job_id, status="done", stage="Done", progress=100, message="Completed",
                       result={"clip_ids": clip_ids, "count": len(clip_ids)})
    except Exception as e:
        await _set_job(job_id, status="error", stage="Error", progress=0, error=str(e), message=str(e))
        async with SessionLocal() as db:
            if project_id:
                p = await db.get(Project, project_id)
                if p:
                    p.status = "error"
                    await db.commit()
    finally:
        try:
            audio_path.unlink(missing_ok=True)
        except Exception:
            pass


def _group_words(words: list, clip_start: float, group_size: int = 4) -> list:
    out = []
    i = 0
    n = len(words)
    while i < n:
        chunk = words[i:i + group_size]
        text = " ".join(w["word"] for w in chunk).strip()
        start = chunk[0]["start"] - clip_start
        end = chunk[-1]["end"] - clip_start
        if start < 0:
            start = 0.0
        if end <= start:
            end = start + 0.5
        out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
        i += group_size
    return out


def storage_rel(p: Path) -> str:
    try:
        return str(p.relative_to(settings.data_dir))
    except Exception:
        return str(p)
