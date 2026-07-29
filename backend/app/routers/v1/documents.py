"""
Document + admin endpoints, versioned under /api/v1.

POST   /api/v1/documents            upload one file -> runs the full ingestion pipeline
GET    /api/v1/documents            list all documents with chunk counts (admin view)
POST   /api/v1/documents/{id}/reindex   re-parse/re-chunk/re-embed one document
DELETE /api/v1/documents/{id}       remove a document, its chunks, and its vectors
"""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import require_api_key
from app.data_access import documents_repo
from app.db.models import Chunk, Document
from app.db.session import get_db
from app.schemas.documents import DocumentOut, IngestResponse, ReindexResponse
from app.services.ingestion import ingest_file, reindex_document
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/v1/documents", tags=["documents"], dependencies=[Depends(require_api_key)])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {"pdf", "docx", "html", "htm", "md", "markdown"}


@router.post("", response_model=IngestResponse)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationAppError(f"Unsupported file type '.{ext}'. Allowed: {sorted(SUPPORTED_EXTENSIONS)}")

    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    title = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()
    document = await ingest_file(db, dest, source_format=ext, title=title)

    return IngestResponse(document=DocumentOut.model_validate(document), chunks_created=document.chunk_count)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return documents_repo.list_documents(db)


@router.post("/{document_id}/reindex", response_model=ReindexResponse)
async def reindex_one(document_id: str, db: Session = Depends(get_db)):
    document = documents_repo.get_document(db, document_id)
    if not document:
        raise NotFoundError(f"Document {document_id} not found")

    path = UPLOAD_DIR / document.filename
    if not path.exists():
        raise ValidationAppError("Original source file is missing from disk; re-upload it instead.")

    count = await reindex_document(db, document, path)
    return ReindexResponse(documents_reindexed=1, total_chunks=count)


@router.post("/reindex-all", response_model=ReindexResponse)
async def reindex_all(db: Session = Depends(get_db)):
    documents = documents_repo.list_documents(db)
    total = 0
    reindexed = 0
    for document in documents:
        path = UPLOAD_DIR / document.filename
        if not path.exists():
            continue
        total += await reindex_document(db, document, path)
        reindexed += 1
    return ReindexResponse(documents_reindexed=reindexed, total_chunks=total)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = documents_repo.get_document(db, document_id)
    if not document:
        raise NotFoundError(f"Document {document_id} not found")

    get_vector_store().delete_by_document(document_id)
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.delete(document)
    db.commit()

    path = UPLOAD_DIR / document.filename
    if path.exists():
        path.unlink()
