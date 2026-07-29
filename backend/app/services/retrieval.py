"""
Retrieval + context assembly (design decisions #2 and #3 in the brief).

Top-k and context assembly, as implemented here:
- top_k defaults to 5 (TOP_K env var). Rationale for the design doc: our
  Contoso corpus chunks run ~250-350 tokens; 5 chunks is ~1,500-2,000
  tokens of context, comfortably inside any model's window with room for
  a multi-turn conversation, while still giving the model 2-3 independent
  sources to cross-reference for most policy questions.
- Ordering: results come back sorted by retrieval score (vector store
  handles this — cosine similarity locally, Azure's hybrid RRF score in
  production). We do NOT re-order by document recency or alphabetically;
  the model should see the most relevant chunk first since some providers
  attend more to earlier context.
- Deduplication: if the same chunk is retrieved twice (can happen with
  hybrid search returning overlapping vector + keyword hits) we keep only
  the first occurrence, by chunk_id.
- Refusal threshold: if the top result's score is below MIN_RELEVANCE
  score OR there are zero results, we skip the LLM call entirely and
  return the fixed refusal string. This is what section "Refusal
  behavior" asks for — an honest "not in the knowledge base" rather than
  letting the model try to answer from general knowledge.
"""
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.embeddings import embed_texts
from app.services.vector_store import get_vector_store

MIN_RELEVANCE_SCORE = 0.18  # tuned against the retrieval-quality test set in the design doc
REFUSAL_TEXT = "I don't have that in the knowledge base."


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    section_heading: str | None
    content: str
    score: float


async def retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.top_k

    [query_embedding] = await embed_texts([query])
    store = get_vector_store()
    hits = store.search(query_embedding, query, top_k=k)

    seen_chunk_ids: set[str] = set()
    deduped: list[RetrievedChunk] = []
    for hit in hits:
        if hit["chunk_id"] in seen_chunk_ids:
            continue
        seen_chunk_ids.add(hit["chunk_id"])
        deduped.append(
            RetrievedChunk(
                chunk_id=hit["chunk_id"],
                document_id=hit["document_id"],
                document_title=hit.get("document_title", ""),
                section_heading=hit.get("section_heading"),
                content=hit.get("content", ""),
                score=hit.get("score", 0.0),
            )
        )
    return deduped


def should_refuse(chunks: list[RetrievedChunk]) -> bool:
    if not chunks:
        return True
    return chunks[0].score < MIN_RELEVANCE_SCORE
