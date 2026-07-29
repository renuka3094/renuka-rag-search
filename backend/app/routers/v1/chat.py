"""
Chat endpoints, versioned under /api/v1.

POST /api/v1/chat/stream
    Server-Sent Events. Each `data:` line is one JSON event:
      {"type": "token", "text": "..."}                      -- streamed answer text
      {"type": "citations", "citations": [...]}              -- sent once, after retrieval
      {"type": "done", "conversation_id": "...", "message_id": "...", "flagged_prompt_injection": bool}

    Refusal path: if retrieval finds nothing relevant, we skip the LLM
    entirely and stream the fixed refusal string as a single token event,
    then "done" with no citations. This guarantees the refusal message is
    never phrased by the model (which could drift over time) — it is
    always the exact same string the brief asks for.

GET /api/v1/chat/conversations/{conversation_id}
    Full history for the multi-turn chat UI to hydrate on reload.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.security import require_api_key
from app.data_access import chat_repo
from app.db.session import SessionLocal, get_db
from app.schemas.chat import ChatRequest, ConversationHistoryOut
from app.services import generation, retrieval
from app.services.guardrails import build_user_turn, detect_injection_attempt
from app.services.retrieval import REFUSAL_TEXT

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"], dependencies=[Depends(require_api_key)])


@router.post("/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db)):
    convo = chat_repo.get_or_create_conversation(db, payload.conversation_id)
    db.commit()
    conversation_id = convo.id  # capture as a plain string now, while `db` is still open

    flagged = detect_injection_attempt(payload.message)
    if flagged:
        log.warning("prompt_injection_pattern_detected", conversation_id=conversation_id, message=payload.message)

    chat_repo.add_message(db, conversation_id, role="user", content=payload.message)
    db.commit()

    async def event_stream():
        # IMPORTANT: FastAPI closes `db` (the Depends(get_db) session) the
        # moment this endpoint function returns — but StreamingResponse
        # keeps running this generator *after* that return, to produce the
        # actual response body. So this generator must never touch `db`;
        # it opens and closes its own session instead, and only ever
        # refers to `conversation_id` as the plain string captured above,
        # never to the `convo` ORM object itself (which becomes invalid
        # the moment its original session closes).
        stream_db = SessionLocal()
        try:
            def sse(event: dict) -> str:
                return f"data: {json.dumps(event)}\n\n"

            chunks = await retrieval.retrieve(payload.message)

            if retrieval.should_refuse(chunks):
                yield sse({"type": "token", "text": REFUSAL_TEXT})
                msg = chat_repo.add_message(stream_db, conversation_id, role="assistant", content=REFUSAL_TEXT, refused=True)
                stream_db.commit()
                yield sse({
                    "type": "done",
                    "conversation_id": conversation_id,
                    "message_id": msg.id,
                    "flagged_prompt_injection": flagged,
                })
                return

            citations_payload = [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "document_title": c.document_title,
                    "snippet": c.content[:280],
                    "rank": i + 1,
                }
                for i, c in enumerate(chunks)
            ]
            yield sse({"type": "citations", "citations": citations_payload})

            context_blocks = [
                {"document_title": c.document_title, "section_heading": c.section_heading, "content": c.content}
                for c in chunks
            ]
            user_turn = build_user_turn(payload.message, context_blocks)

            full_answer = []
            try:
                async for token in generation.stream_answer(user_turn):
                    full_answer.append(token)
                    yield sse({"type": "token", "text": token})
            except Exception as e:  # noqa: BLE001
                log.error("generation_stream_failed", conversation_id=conversation_id, error=str(e))
                yield sse({"type": "error", "message": str(e)})
                return

            answer_text = "".join(full_answer).strip() or REFUSAL_TEXT
            msg = chat_repo.add_message(stream_db, conversation_id, role="assistant", content=answer_text)
            chat_repo.add_citations(stream_db, msg.id, citations_payload)
            stream_db.commit()

            yield sse({
                "type": "done",
                "conversation_id": conversation_id,
                "message_id": msg.id,
                "flagged_prompt_injection": flagged,
            })
        finally:
            stream_db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    convo = chat_repo.get_conversation_with_messages(db, conversation_id)
    if not convo:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return ConversationHistoryOut(conversation=convo, messages=convo.messages)
