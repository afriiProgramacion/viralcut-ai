from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = "Untitled"
    config: Optional[dict] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    status: str
    video_id: Optional[str] = None
    last_job_id: Optional[str] = None
    config: Optional[dict] = None
    class Config:
        from_attributes = True


class VideoOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    filename: str
    size_bytes: int
    duration: float
    width: int
    height: int
    mime: str
    created_at: datetime
    class Config:
        from_attributes = True


class UploadConfig(BaseModel):
    clip_count: int = 5  # 3,5,10,0 auto
    clip_duration: int = 30  # 15,30,45,60,90
    platform: str = "tiktok"  # tiktok|reels|shorts
    language: str = "auto"
    subtitle_style: str = "hormozi"
    cut_aggressiveness: str = "balanced"  # soft|balanced|aggressive
    priority: str = "mixed"  # entertainment|controversy|education|humor|storytelling|mixed


class JobOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    video_id: Optional[str] = None
    type: str
    status: str
    progress: int
    stage: str
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class ClipOut(BaseModel):
    id: str
    project_id: str
    video_id: str
    start: float
    end: float
    duration: float
    title: str
    titles: list[str] = []
    description: str = ""
    hashtags: list[str] = []
    hook: str = ""
    category: str = "mixed"
    viral_score: int = 0
    score_breakdown: dict = {}
    explanation: str = ""
    subtitle_style: str = "hormozi"
    subtitles: list = []
    file_path: Optional[str] = None
    thumb_path: Optional[str] = None
    status: str = "generated"
    created_at: datetime
    class Config:
        from_attributes = True


class ClipEdit(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None
    title: Optional[str] = None
    subtitle_style: Optional[str] = None
    subtitles: Optional[list] = None


class SettingsIn(BaseModel):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    whisper_model: Optional[str] = None
    whisper_device: Optional[str] = None
    whisper_compute_type: Optional[str] = None
    max_upload_mb: Optional[int] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None


class SettingsOut(BaseModel):
    ai_provider: str
    ai_model: str
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    max_upload_mb: int
    has_anthropic: bool
    has_openai: bool
    anthropic_api_key_masked: str
    openai_api_key_masked: str
    ollama_url: str
    ollama_model: str
