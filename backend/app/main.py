from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unhandled_exception_handler
from app.core.logging import configure_logging, get_logger
from app.routers.v1 import chat, documents

settings = get_settings()
configure_logging(settings.env)
log = get_logger(__name__)

Path("data/uploads").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="DataFactZ internal RAG knowledge chatbot — Week 1 Use Case 1.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/v1/health", tags=["health"])
def health():
    return {"status": "ok", "env": settings.env}


@app.on_event("startup")
async def on_startup():
    log.info("app_startup", vector_backend=settings.vector_backend, generation_provider=settings.generation_provider)
