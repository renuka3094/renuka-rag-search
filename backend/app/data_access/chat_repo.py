from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Citation, Conversation, Message


def get_or_create_conversation(db: Session, conversation_id: str | None) -> Conversation:
    if conversation_id:
        convo = db.get(Conversation, conversation_id)
        if convo:
            return convo
    convo = Conversation()
    db.add(convo)
    db.flush()
    return convo


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    refused: bool = False,
    model: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        refused=refused,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    db.add(message)
    db.flush()
    return message


def get_usage_stats(db: Session) -> dict:
    """Aggregated usage numbers for the admin analytics view. Token counts
    are estimates (same tokenizer used for chunk sizing, see
    services/chunking.py), not exact provider-billed counts — good enough
    to compare relative cost/volume across providers, not for invoicing."""
    conversations = db.scalar(select(func.count(Conversation.id))) or 0
    questions = db.scalar(select(func.count(Message.id)).where(Message.role == "user")) or 0

    token_sum = func.coalesce(func.sum(Message.prompt_tokens), 0) + func.coalesce(
        func.sum(Message.completion_tokens), 0
    )
    total_tokens = db.scalar(select(token_sum)) or 0

    by_model_rows = db.execute(
        select(Message.model, func.count(Message.id), token_sum)
        .where(Message.role == "assistant", Message.refused.is_(False), Message.model.is_not(None))
        .group_by(Message.model)
        .order_by(token_sum.desc())
    ).all()

    return {
        "conversations": conversations,
        "questions": questions,
        "total_tokens": int(total_tokens),
        "by_model": [
            {"model": row[0], "message_count": row[1], "tokens": int(row[2])} for row in by_model_rows
        ],
    }


def add_citations(db: Session, message_id: str, citations: list[dict]) -> None:
    # citations dicts carry a few frontend-display-only keys (e.g.
    # section_heading, for the Sources panel) that aren't columns on the
    # Citation model — only pass through what it actually accepts.
    for c in citations:
        db.add(
            Citation(
                message_id=message_id,
                chunk_id=c["chunk_id"],
                document_id=c["document_id"],
                document_title=c["document_title"],
                snippet=c["snippet"],
                rank=c["rank"],
            )
        )


def get_conversation_with_messages(db: Session, conversation_id: str) -> Conversation | None:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
    )
    return db.scalars(stmt).first()


def recent_history(db: Session, conversation_id: str, max_messages: int = 8) -> list[Message]:
    """
    Where conversation history lives / how much goes into each prompt
    (design decision #5): history lives in Postgres/SQLite (the
    `messages` table), not in-memory and not client-side. We send only
    the last `max_messages` turns (default 8 = 4 user/assistant pairs)
    into the prompt, not the full thread. Policy Q&A rarely depends on
    turns older than that, and capping it bounds token cost per request
    regardless of how long a conversation runs.
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
    )
    return list(reversed(list(db.scalars(stmt))))
