from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.schemas import DeleteResponse, IndexInfo
from app.services.vector_store import delete_index, list_indices

router = APIRouter(prefix="/indices", tags=["indices"])


@router.get("/", response_model=list[IndexInfo])
async def list_all_indices():
    raw = list_indices()
    return [
        IndexInfo(
            index_id=r["index_id"],
            filename=r["filename"],
            chunks=r["chunks"],
            created_at=datetime.fromisoformat(r["created_at"]),
            size_bytes=r["size_bytes"],
        )
        for r in raw
    ]


@router.delete("/{index_id}", response_model=DeleteResponse)
async def delete_index_by_id(index_id: str):
    try:
        delete_index(index_id)
        return DeleteResponse(index_id=index_id, message="Index deleted successfully")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")
