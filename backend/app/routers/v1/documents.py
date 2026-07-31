"""
Document + admin endpoints, versioned under /api/v1.

The knowledge base is a fixed corpus (see corpus/generate_corpus.py) —
there is intentionally no upload endpoint. Adding a document means
regenerating the corpus and ingesting it via a one-off script, not
through this API.

GET    /api/v1/documents            list all documents with chunk counts (admin view)
POST   /api/v1/documents/{id}/reindex   re-parse/re-chunk/re-embed one document

There is intentionally no delete endpoint either — removing a document
from the fixed corpus means editing corpus/generate_corpus.py and
re-provisioning, not an admin-UI action.
"""
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.core.security import require_api_key
from app.data_access import documents_repo
from app.db.session import get_db
from app.schemas.documents import DocumentOut, ReindexResponse
from app.services.ingestion import reindex_document

router = APIRouter(prefix="/api/v1/documents", tags=["documents"], dependencies=[Depends(require_api_key)])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
