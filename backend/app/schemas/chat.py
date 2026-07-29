import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None, description="Omit to start a new conversation."
    )
    message: str = Field(min_length=1, max_length=4000)


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    document_title: str
    snippet: str
    rank: int


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    refused: bool
    created_at: dt.datetime
    citations: list[CitationOut] = []


class ChatResponse(BaseModel):
    conversation_id: str
    message: MessageOut
    flagged_prompt_injection: bool = False


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: dt.datetime


class ConversationHistoryOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]
