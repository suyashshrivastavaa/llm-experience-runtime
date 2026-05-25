from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    artifacts_dir: Path = Path("artifacts")
    indices_dir: Path = Path("indices")

    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
