from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Local (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Cloud (HuggingFace) — set this on Render
    hf_api_token: Optional[str] = None
    hf_model: str = "mistralai/Mistral-7B-Instruct-v0.3"

    artifacts_dir: Path = Path("artifacts")
    indices_dir: Path = Path("indices")

    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_k: int = 4

    @property
    def use_huggingface(self) -> bool:
        return bool(self.hf_api_token)

    class Config:
        env_file = ".env"


settings = Settings()
