import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def uid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String, default="Untitled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="created")  # created|processing|done|error
    video_id: Mapped[str | None] = mapped_column(String, ForeignKey("videos.id"), nullable=True)
    last_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    videos: Mapped[list["Video"]] = relationship(back_populates="project", cascade="all, delete-orphan", foreign_keys="Video.project_id")
    clips: Mapped[list["Clip"]] = relationship(back_populates="project", cascade="all, delete-orphan", foreign_keys="Clip.project_id")


class Video(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str | None] = mapped_column(String, ForeignKey("projects.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String)
    original_path: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped["Project | None"] = relationship(back_populates="videos", foreign_keys=[project_id])
    transcription: Mapped["Transcription | None"] = relationship(back_populates="video", uselist=False, cascade="all, delete-orphan")


class Transcription(Base):
    __tablename__ = "transcriptions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"), unique=True)
    language: Mapped[str] = mapped_column(String, default="auto")
    full_text: Mapped[str] = mapped_column(Text, default="")
    segments: Mapped[list] = mapped_column(JSON, default=list)
    words: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    video: Mapped["Video"] = relationship(back_populates="transcription")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str | None] = mapped_column(String, ForeignKey("projects.id"), nullable=True)
    video_id: Mapped[str | None] = mapped_column(String, ForeignKey("videos.id"), nullable=True)
    type: Mapped[str] = mapped_column(String)  # upload_analyze|process|export
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|running|done|error|cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String, default="queued")
    message: Mapped[str] = mapped_column(String, default="")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Clip(Base):
    __tablename__ = "clips"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"))
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String, default="")
    titles: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    hook: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String, default="mixed")
    viral_score: Mapped[int] = mapped_column(Integer, default=0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    subtitle_style: Mapped[str] = mapped_column(String, default="hormozi")
    subtitles: Mapped[list] = mapped_column(JSON, default=list)  # word-level segments
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    thumb_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="generated")  # generated|edited|exported
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped["Project"] = relationship(back_populates="clips", foreign_keys=[project_id])


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
