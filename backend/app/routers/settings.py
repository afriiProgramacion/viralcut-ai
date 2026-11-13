from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models import Setting
from ..schemas import SettingsIn, SettingsOut
from ..config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

KEYS = ["anthropic_api_key", "openai_api_key", "ai_provider", "ai_model",
        "whisper_model", "whisper_device", "whisper_compute_type", "max_upload_mb"]


async def _get(db, key, default=""):
    r = await db.get(Setting, key)
    return r.value if r else default


async def _set(db, key, value):
    r = await db.get(Setting, key)
    if r:
        r.value = value
    else:
        db.add(Setting(key=key, value=value))


def mask(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 8:
        return "••••"
    return v[:4] + "•" * (len(v) - 8) + v[-4:]


@router.get("", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    anthropic = await _get(db, "anthropic_api_key", settings.anthropic_api_key)
    openai = await _get(db, "openai_api_key", settings.openai_api_key)
    provider = await _get(db, "ai_provider", settings.ai_provider)
    model = await _get(db, "ai_model", settings.ai_model)
    wm = await _get(db, "whisper_model", settings.whisper_model)
    wd = await _get(db, "whisper_device", settings.whisper_device)
    wc = await _get(db, "whisper_compute_type", settings.whisper_compute_type)
    mu = await _get(db, "max_upload_mb", str(settings.max_upload_mb))
    ou = await _get(db, "ollama_url", "http://localhost:11434")
    om = await _get(db, "ollama_model", "llama3.2")
    return SettingsOut(
        ai_provider=provider,
        ai_model=model,
        whisper_model=wm,
        whisper_device=wd,
        whisper_compute_type=wc,
        max_upload_mb=int(mu or settings.max_upload_mb),
        has_anthropic=bool(anthropic),
        has_openai=bool(openai),
        anthropic_api_key_masked=mask(anthropic),
        openai_api_key_masked=mask(openai),
        ollama_url=ou,
        ollama_model=om,
    )


@router.put("")
async def update_settings(body: SettingsIn, db: AsyncSession = Depends(get_db)):
    if body.anthropic_api_key is not None:
        await _set(db, "anthropic_api_key", body.anthropic_api_key)
    if body.openai_api_key is not None:
        await _set(db, "openai_api_key", body.openai_api_key)
    if body.ai_provider is not None:
        await _set(db, "ai_provider", body.ai_provider)
    if body.ai_model is not None:
        await _set(db, "ai_model", body.ai_model)
    if body.whisper_model is not None:
        await _set(db, "whisper_model", body.whisper_model)
    if body.whisper_device is not None:
        await _set(db, "whisper_device", body.whisper_device)
    if body.whisper_compute_type is not None:
        await _set(db, "whisper_compute_type", body.whisper_compute_type)
    if body.max_upload_mb is not None:
        await _set(db, "max_upload_mb", str(body.max_upload_mb))
    if body.ollama_url is not None:
        await _set(db, "ollama_url", body.ollama_url)
    if body.ollama_model is not None:
        await _set(db, "ollama_model", body.ollama_model)
    await db.commit()
    return {"ok": True}


@router.get("/health")
async def health():
    return {"status": "ok", "ffmpeg": True}
