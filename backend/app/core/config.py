"""
Centralized configuration.

Why a dedicated settings module:
- Section 6.2 requires "configuration via environment variables". Reading
  os.environ scattered across the codebase makes it impossible to see,
  at a glance, everything the app depends on, and it breaks type safety.
  pydantic-settings gives us one typed, validated object imported everywhere.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "DataFactZ RAG Chatbot"
    env: str = "local"
    api_key: str = "change-me-dev-key"
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Vector backend
    vector_backend: str = "local"  # "local" | "azure"
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "contoso-kb"

    # Embeddings
    embeddings_provider: str = "azure_openai"
    embeddings_model: str = "text-embedding-3-small"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_embeddings_deployment: str = "text-embedding-3-small"
    azure_foundry_api_version: str = "2024-05-01-preview"

    # Generation
    generation_provider: str = "azure_openai"  # "azure_openai" | "azure_foundry" | "azure_v1" | "claude" | "deepseek"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    # DeepSeek reached through the shared Azure AI Foundry project (same
    # endpoint/key as azure_v1, different deployment name) — used by the
    # in-UI model switcher's "DeepSeek (Azure)" option. Distinct from
    # deepseek_api_key/deepseek_base_url below, which are for calling
    # DeepSeek's own platform directly (a separate account/key).
    azure_deepseek_deployment: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Retrieval tuning
    chunk_size_tokens: int = 350
    chunk_overlap_tokens: int = 60
    top_k: int = 5

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
