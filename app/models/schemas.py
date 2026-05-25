from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IngestResponse(BaseModel):
    index_id: str
    filename: str
    chunks_indexed: int
    message: str


class IndexInfo(BaseModel):
    index_id: str
    filename: str
    chunks: int
    created_at: datetime
    size_bytes: int


class QueryRequest(BaseModel):
    query: str
    index_id: str
    k: Optional[int] = None
    stream: bool = False


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    index_id: str


class DeleteResponse(BaseModel):
    index_id: str
    message: str
