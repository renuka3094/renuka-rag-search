"""
Relational schema.

ERD (put this in the design doc as a diagram too — this is the text version):

  documents 1---* chunks
  conversations 1---* messages
  messages 1---* citations *---1 chunks
                            *---1 documents   (denormalized doc_id for fast display without a join)

Why this shape:
- documents/chunks is the ingestion side: one row per source file, one row
  per chunk we embedded and indexed. chunk_count on documents is a
  denormalized counter the admin view reads without a COUNT(*) query.
- conversations/messages is standard chat history. Kept separate from
  citations so a message can have 0..N citations (assistant messages have
  citations, user messages never do).
- citations is its own table (not a JSON column on messages) so we can
  index it, query "which documents get cited most" for product analytics,
  and enforce referential integrity back to the chunk that was actually
  retrieved.

Indexes: every foreign key used in a WHERE/JOIN is indexed explicitly
(SQLite/Postgres don't always auto-index FKs the way MySQL does).
"""
import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(512))
    source_format: Mapped[str] = mapped_column(String(16))  # pdf | docx | html | md
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|indexed|failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer)  # position within the document
    section_heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    # id of the vector in the vector store (Azure AI Search key, or local store key)
    vector_ref: Mapped[str] = mapped_column(String(64))

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (Index("ix_chunks_document_id", "document_id"),)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(256), default="New conversation")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    refused: Mapped[bool] = mapped_column(default=False)  # True when we returned the "not in KB" refusal
    # model/token_counts are set only on assistant messages, for the usage analytics view
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_messages_conversation_id", "conversation_id"),)


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    document_title: Mapped[str] = mapped_column(String(512))  # denormalized for fast render
    snippet: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)  # 1 = most relevant

    message: Mapped["Message"] = relationship(back_populates="citations")

    __table_args__ = (
        Index("ix_citations_message_id", "message_id"),
        Index("ix_citations_chunk_id", "chunk_id"),
    )
