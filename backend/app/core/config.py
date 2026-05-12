from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Recon Platform"
    database_url: str = f"sqlite:///{BASE_DIR / 'recon.db'}"
    storage_dir: Path = BASE_DIR / "storage"
    residual_tolerance: float = 1.0          # USD; closing-equation threshold
    amount_tolerance_abs: float = 0.50       # USD; absolute tolerance for Pass 2
    amount_tolerance_pct: float = 0.005      # 0.5% relative tolerance for Pass 2
    cors_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
