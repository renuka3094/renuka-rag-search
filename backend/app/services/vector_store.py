"""
Vector store abstraction.

Why an abstraction instead of calling Azure AI Search directly everywhere:
- Section 3 requires Azure AI Search as the default, but local dev/CI
  shouldn't need a live Azure resource just to run unit tests on chunking.
- VECTOR_BACKEND=local uses a flat numpy cosine-similarity index persisted
  to disk (data/vector_store.json). Fine up to a few tens of thousands of
  chunks — nowhere near production scale, but perfect for a Week-1 corpus
  of 15-30 documents.
- VECTOR_BACKEND=azure uses Azure AI Search's hybrid (vector + BM25
  keyword) search, which is what you actually defend in the design doc as
  the production choice: hybrid beats pure vector on exact-term queries
  like policy names, form numbers, or acronyms that embeddings alone
  under-weight.

Both implementations share the same interface: upsert(...) / search(...) /
delete_by_document(...), so services/retrieval.py never needs to know which
backend is active.
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.errors import UpstreamProviderError


class VectorRecord:
    def __init__(self, vector_id: str, document_id: str, chunk_id: str, embedding: list[float], metadata: dict[str, Any]):
        self.vector_id = vector_id
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.embedding = embedding
        self.metadata = metadata


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def search(self, query_embedding: list[float], query_text: str, top_k: int) -> list[dict]: ...

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None: ...


class LocalVectorStore(VectorStore):
    """Flat cosine-similarity store, persisted as JSON. Dev/demo only."""

    def __init__(self, path: str = "data/vector_store.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            self._records = json.loads(self.path.read_text())

    def _save(self):
        self.path.write_text(json.dumps(self._records))

    def upsert(self, records: list[VectorRecord]) -> None:
        for r in records:
            self._records[r.vector_id] = {
                "document_id": r.document_id,
                "chunk_id": r.chunk_id,
                "embedding": r.embedding,
                "metadata": r.metadata,
            }
        self._save()

    def search(self, query_embedding: list[float], query_text: str, top_k: int) -> list[dict]:
        if not self._records:
            return []
        q = np.array(query_embedding)
        q_norm = np.linalg.norm(q) or 1e-8

        scored = []
        query_terms = set(query_text.lower().split())
        for vector_id, rec in self._records.items():
            v = np.array(rec["embedding"])
            v_norm = np.linalg.norm(v) or 1e-8
            cosine = float(np.dot(q, v) / (q_norm * v_norm))

            # Cheap keyword boost so this local store approximates "hybrid"
            # search too, for parity with the Azure backend during dev.
            content = rec["metadata"].get("content", "").lower()
            keyword_overlap = len(query_terms & set(content.split()))
            score = cosine + 0.02 * keyword_overlap

            scored.append((score, vector_id, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        return [
            {
                "vector_id": vid,
                "document_id": rec["document_id"],
                "chunk_id": rec["chunk_id"],
                "score": score,
                **rec["metadata"],
            }
            for score, vid, rec in top
        ]

    def delete_by_document(self, document_id: str) -> None:
        self._records = {k: v for k, v in self._records.items() if v["document_id"] != document_id}
        self._save()


class AzureSearchVectorStore(VectorStore):
    """Hybrid vector + keyword search via Azure AI Search."""

    def __init__(self):
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient

        settings = get_settings()
        if not settings.azure_search_endpoint or not settings.azure_search_api_key:
            raise UpstreamProviderError("Azure AI Search is not configured (endpoint/key missing).")

        credential = AzureKeyCredential(settings.azure_search_api_key)
        self.index_name = settings.azure_search_index_name
        self.index_client = SearchIndexClient(settings.azure_search_endpoint, credential)
        self.client = SearchClient(settings.azure_search_endpoint, self.index_name, credential)
        self._ensure_index()

    def _ensure_index(self):
        from azure.search.documents.indexes.models import (
            SearchIndex, SimpleField, SearchableField, SearchFieldDataType,
            VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile, SearchField,
        )

        existing = [i.name for i in self.index_client.list_indexes()]
        if self.index_name in existing:
            return

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-cfg")],
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-cfg")],
        )
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="document_title", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="section_heading", type=SearchFieldDataType.String),
            SearchField(
                name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=1536, vector_search_profile_name="hnsw-profile",
            ),
        ]
        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
        self.index_client.create_index(index)

    def upsert(self, records: list[VectorRecord]) -> None:
        docs = []
        for r in records:
            docs.append({
                "id": r.vector_id,
                "document_id": r.document_id,
                "chunk_id": r.chunk_id,
                "content": r.metadata.get("content", ""),
                "document_title": r.metadata.get("document_title", ""),
                "section_heading": r.metadata.get("section_heading") or "",
                "embedding": r.embedding,
            })
        self.client.upload_documents(docs)

    def search(self, query_embedding: list[float], query_text: str, top_k: int) -> list[dict]:
        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(vector=query_embedding, k_nearest_neighbors=top_k, fields="embedding")
        results = self.client.search(
            search_text=query_text,  # keyword half of hybrid search
            vector_queries=[vector_query],
            top=top_k,
        )
        out = []
        for r in results:
            out.append({
                "vector_id": r["id"],
                "document_id": r["document_id"],
                "chunk_id": r["chunk_id"],
                "content": r["content"],
                "document_title": r["document_title"],
                "section_heading": r.get("section_heading"),
                "score": r.get("@search.score", 0.0),
            })
        return out

    def delete_by_document(self, document_id: str) -> None:
        results = list(self.client.search(search_text="*", filter=f"document_id eq '{document_id}'"))
        if results:
            self.client.delete_documents([{"id": r["id"]} for r in results])


_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    settings = get_settings()
    if settings.vector_backend == "azure":
        _store_instance = AzureSearchVectorStore()
    else:
        _store_instance = LocalVectorStore()
    return _store_instance
