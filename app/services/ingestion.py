import hashlib
import shutil
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from app.core.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _derive_index_id(filename: str) -> str:
    return hashlib.sha1(filename.encode()).hexdigest()[:12]


def _get_loader(path: Path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(str(path))
    elif ext == ".txt":
        return TextLoader(str(path), encoding="utf-8")
    elif ext == ".md":
        return TextLoader(str(path), encoding="utf-8")
    raise ValueError(f"Unsupported file type: {ext}")


def ingest_file(file_bytes: bytes, filename: str) -> tuple[str, list]:
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = settings.artifacts_dir / filename
    artifact_path.write_bytes(file_bytes)

    loader = _get_loader(artifact_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(docs)

    index_id = _derive_index_id(filename)
    return index_id, chunks
