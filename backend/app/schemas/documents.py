import datetime as dt

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    title: str
    source_format: str
    status: str
    chunk_count: int
    uploaded_at: dt.datetime
    indexed_at: dt.datetime | None = None


class IngestResponse(BaseModel):
    document: DocumentOut
    chunks_created: int


class ReindexResponse(BaseModel):
    documents_reindexed: int
    total_chunks: int
