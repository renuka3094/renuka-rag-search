"""
Ingestion pipeline: load -> parse -> chunk -> embed -> index -> persist.

This is the one place all five steps happen in order, so it is the
function to point at in review when asked "walk me through what happens
when a document is added."
"""
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.services.chunking import chunk_sections
from app.services.embeddings import embed_texts
from app.services.parsers import parse_document
from app.services.vector_store import VectorRecord, get_vector_store


async def ingest_file(db: Session, path: Path, source_format: str, title: str) -> Document:
    document = Document(filename=path.name, title=title, source_format=source_format, status="pending")
    db.add(document)
    db.flush()  # assigns document.id without committing yet

    sections = parse_document(path)
    candidates = chunk_sections(sections)

    if not candidates:
        document.status = "failed"
        db.commit()
        return document

    embeddings = await embed_texts([c.content for c in candidates])

    store = get_vector_store()
    records = []
    db_chunks = []
    for candidate, embedding in zip(candidates, embeddings):
        vector_id = str(uuid.uuid4())
        chunk = Chunk(
            document_id=document.id,
            ordinal=candidate.ordinal,
            section_heading=candidate.section_heading,
            content=candidate.content,
            token_count=candidate.token_count,
            vector_ref=vector_id,
        )
        db.add(chunk)
        db_chunks.append(chunk)
        records.append(
            VectorRecord(
                vector_id=vector_id,
                document_id=document.id,
                chunk_id=chunk.id,
                embedding=embedding,
                metadata={
                    "content": candidate.content,
                    "document_title": title,
                    "section_heading": candidate.section_heading,
                },
            )
        )

    db.flush()  # ensure chunk.id values exist before we write them into the vector store metadata
    # chunk.id is assigned on flush by the default=_uuid callable; re-sync vector records with real chunk ids
    for record, chunk in zip(records, db_chunks):
        record.chunk_id = chunk.id

    store.upsert(records)

    document.status = "indexed"
    document.chunk_count = len(db_chunks)
    from sqlalchemy import func
    document.indexed_at = func.now()

    db.commit()
    db.refresh(document)
    return document


async def reindex_document(db: Session, document: Document, path: Path) -> int:
    """Delete a document's existing vectors + chunk rows and re-run ingestion.
    Used by the admin 're-index' button after a source file is replaced."""
    store = get_vector_store()
    store.delete_by_document(document.id)
    db.query(Chunk).filter(Chunk.document_id == document.id).delete()
    db.commit()

    sections = parse_document(path)
    candidates = chunk_sections(sections)
    embeddings = await embed_texts([c.content for c in candidates]) if candidates else []

    records = []
    for candidate, embedding in zip(candidates, embeddings):
        vector_id = str(uuid.uuid4())
        chunk = Chunk(
            document_id=document.id,
            ordinal=candidate.ordinal,
            section_heading=candidate.section_heading,
            content=candidate.content,
            token_count=candidate.token_count,
            vector_ref=vector_id,
        )
        db.add(chunk)
        db.flush()
        records.append(
            VectorRecord(
                vector_id=vector_id,
                document_id=document.id,
                chunk_id=chunk.id,
                embedding=embedding,
                metadata={
                    "content": candidate.content,
                    "document_title": document.title,
                    "section_heading": candidate.section_heading,
                },
            )
        )

    if records:
        store.upsert(records)

    document.chunk_count = len(records)
    document.status = "indexed"
    from sqlalchemy import func
    document.indexed_at = func.now()
    db.commit()
    return len(records)
