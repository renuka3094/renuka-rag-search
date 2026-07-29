from sqlalchemy import select
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


def add_message(db: Session, conversation_id: str, role: str, content: str, refused: bool = False) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content, refused=refused)
    db.add(message)
    db.flush()
    return message


def add_citations(db: Session, message_id: str, citations: list[dict]) -> None:
    for c in citations:
        db.add(Citation(message_id=message_id, **c))


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
