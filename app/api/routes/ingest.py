from fastapi import APIRouter, HTTPException, UploadFile, File

from app.models.schemas import IngestResponse
from app.services.ingestion import ingest_file
from app.services.vector_store import save_index

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/", response_model=IngestResponse)
async def ingest_artifact(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        index_id, chunks = ingest_file(file_bytes, file.filename)
        chunks_indexed = save_index(index_id, chunks, file.filename)
        return IngestResponse(
            index_id=index_id,
            filename=file.filename,
            chunks_indexed=chunks_indexed,
            message="Artifact ingested and indexed successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
