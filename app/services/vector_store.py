import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.core.config import settings

_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        if settings.use_huggingface:
            # Cloud: use HF Inference API — no local model loaded, saves ~200MB RAM
            from langchain_huggingface import HuggingFaceEndpointEmbeddings
            _embeddings = HuggingFaceEndpointEmbeddings(
                model="sentence-transformers/all-MiniLM-L6-v2",
                huggingfacehub_api_token=settings.hf_api_token,
            )
        else:
            # Local: run embeddings on-device via sentence-transformers
            from langchain_huggingface import HuggingFaceEmbeddings
            _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


def _meta_path(index_id: str) -> Path:
    return settings.indices_dir / index_id / "meta.json"


def _index_path(index_id: str) -> Path:
    return settings.indices_dir / index_id / "faiss"


def save_index(index_id: str, chunks: list, filename: str) -> int:
    embeddings = _get_embeddings()
    store = FAISS.from_documents(chunks, embeddings)

    index_dir = settings.indices_dir / index_id
    index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(_index_path(index_id)))

    meta = {
        "index_id": index_id,
        "filename": filename,
        "chunks": len(chunks),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": sum(
            f.stat().st_size for f in _index_path(index_id).rglob("*") if f.is_file()
        ),
    }
    _meta_path(index_id).write_text(json.dumps(meta))
    return len(chunks)


def load_index(index_id: str) -> FAISS:
    path = _index_path(index_id)
    if not path.exists():
        raise FileNotFoundError(f"Index '{index_id}' not found")
    return FAISS.load_local(
        str(path), _get_embeddings(), allow_dangerous_deserialization=True
    )


def list_indices() -> list[dict]:
    indices = []
    for meta_file in settings.indices_dir.glob("*/meta.json"):
        indices.append(json.loads(meta_file.read_text()))
    return indices


def delete_index(index_id: str) -> None:
    index_dir = settings.indices_dir / index_id
    if not index_dir.exists():
        raise FileNotFoundError(f"Index '{index_id}' not found")
    shutil.rmtree(index_dir)


def index_exists(index_id: str) -> bool:
    return _index_path(index_id).exists()
