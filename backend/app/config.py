import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "ViralCut AI"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path | None = None
    uploads_dir: Path | None = None
    outputs_dir: Path | None = None
    temp_dir: Path | None = None

    # DB
    database_url: str = "sqlite+aiosqlite:///./data/viralcut.db"

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_provider: str = "anthropic"  # anthropic | openai | local
    ai_model: str = ""  # override

    # Whisper
    whisper_model: str = "tiny"  # tiny/base/small/medium (tiny = fastest)
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Processing
    max_upload_mb: int = 2048
    target_fps: int = 30
    output_width: int = 1080
    output_height: int = 1920

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **data):
        super().__init__(**data)
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.uploads_dir is None:
            self.uploads_dir = self.data_dir / "uploads"
        if self.outputs_dir is None:
            self.outputs_dir = self.data_dir / "outputs"
        if self.temp_dir is None:
            self.temp_dir = self.data_dir / "temp"
        for d in (self.data_dir, self.uploads_dir, self.outputs_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite"):
            # ensure relative path resolved to data dir
            pass


settings = Settings()
os.environ.setdefault("VIRALCUT_DATA", str(settings.data_dir))
