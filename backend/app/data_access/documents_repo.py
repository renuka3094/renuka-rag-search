"""
Data access layer for documents. Routers/services never write raw SQLAlchemy
queries directly — they call these functions. This is the "layered backend
(routers -> services -> data access)" requirement in Section 6.2: it keeps
query logic in one place so an index or query change doesn't ripple through
route handlers.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.uploaded_at.desc())))


def get_document(db: Session, document_id: str) -> Document | None:
    return db.get(Document, document_id)
