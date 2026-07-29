# Solution Design Document — Contoso Knowledge Assistant (RAG Chatbot)

**Program:** DataFactZ AI Engineering Internship — Week 1, Use Case 1
**Author:** *[your name]*
**Date:** *[fill in]*

> This is a working first draft generated alongside the codebase. Fill in
> the bracketed placeholders with your own measurements before submitting —
> particularly the retrieval-quality table (Section 8) and cost estimate
> (Section 9), which need numbers from your own test run, not assumed ones.

---

## 1. Problem Statement

**Business framing.** Contoso Corp employees currently ask HR and IT
recurring questions about policies, benefits, and procedures over email
and Slack, consuming staff time on repetitive lookups and producing
inconsistent answers depending on who responds. A grounded internal
chatbot reduces that load and gives every employee the same, correct,
source-cited answer.

**User.** Any Contoso Corp employee, from any device, asking natural-
language questions about company policy.

**Success criteria.**
- Answers are grounded exclusively in the indexed corpus, never the
  model's general knowledge.
- Out-of-scope questions are refused honestly rather than hallucinated.
- Every answer is traceable to a specific source document and section.
- Admins can see what's indexed and re-index after a source-document
  update without a code deploy.

**Out of scope (Week 1).**
- Single sign-on / per-user identity (this pilot uses one shared API key).
- Multi-language support.
- Automated evaluation harness (stretch goal, not core).
- Write-back workflows (e.g. actually submitting a PTO request).

---

## 2. Architecture

```
                    ┌─────────────────────┐
                    │   React frontend     │
                    │ (Chat + Admin pages) │
                    └──────────┬───────────┘
                               │ REST + SSE, X-API-Key
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI backend    │
                    │ routers → services → │
                    │     data access      │
                    └──┬─────────┬─────────┘
                       │         │
        ┌──────────────┘         └───────────────┐
        ▼                                         ▼
┌───────────────┐                       ┌───────────────────┐
│ SQLite/Postgres│                      │ Azure AI Search     │
│ documents,     │                      │ (hybrid vector +    │
│ chunks,        │                      │  keyword index)     │
│ conversations,  │                     └─────────┬───────────┘
│ messages,       │                               │
│ citations       │                               │
└───────────────┘                                 │
        ▲                                         │
        │              ┌──────────────────────────┘
        │              ▼
        │   ┌─────────────────────┐        ┌─────────────────────┐
        └───┤ Ingestion pipeline    │──────▶│ Azure OpenAI /        │
            │ parse→chunk→embed     │       │ DeepSeek / Claude     │
            └─────────────────────┘        │ (generation + embed) │
                                             └─────────────────────┘
```

**Components:**
- **Frontend (React + Vite):** Chat page (multi-turn, streaming, citation
  pills) and Admin page (document list, chunk counts, upload, re-index,
  delete). Shared layout shell reused across all three Week apps.
- **Backend (FastAPI):** layered `routers → services → data_access`.
  Routers only validate input and call services; services hold business
  logic (chunking, retrieval, generation, guardrails); data_access holds
  all SQL.
- **Relational database:** SQLite locally, swappable to Azure Database
  for PostgreSQL for a real deployment by changing one `DATABASE_URL`.
- **Vector store:** Azure AI Search (hybrid vector + keyword) in
  production; a local numpy cosine-similarity store for zero-cost dev,
  selected by `VECTOR_BACKEND`.
- **LLM providers:** Azure OpenAI, Azure AI Foundry, DeepSeek, or Claude
  for generation (all implement the same streaming interface); Azure
  OpenAI for embeddings (see Section 7 for why DeepSeek isn't used there).

## 3. Data Flow

1. Admin uploads a document → saved to disk → `ingest_file()` runs:
   parse (format-specific) → chunk (structure-aware, token-bounded) →
   embed (batch call) → upsert into the vector store → persist `Document`
   + `Chunk` rows.
2. Employee sends a chat message → backend embeds the query → vector
   store hybrid search returns top-k chunks → **refusal check**: if the
   top score is below threshold, return the fixed refusal string without
   calling the LLM → otherwise assemble a numbered context block, call
   the LLM with the hardened system prompt, stream tokens back over SSE →
   persist the assistant `Message` + its `Citation` rows.
3. Admin can re-index a document (e.g. after replacing the source file)
   without touching any other document's index entries.

## 4. Database Design (ERD)

```
documents ───1:N─── chunks
conversations ───1:N─── messages ───1:N─── citations ───N:1─── chunks
                                                        └─N:1─── documents
```

| Table | Key columns | Notes |
|---|---|---|
| `documents` | id (PK), filename, title, source_format, status, chunk_count, uploaded_at, indexed_at | `chunk_count` is denormalized so the admin view never runs a `COUNT(*)` |
| `chunks` | id (PK), document_id (FK, indexed), ordinal, section_heading, content, token_count, vector_ref | `vector_ref` is the id used to look the vector up in whichever vector store backend is active |
| `conversations` | id (PK), title, created_at | |
| `messages` | id (PK), conversation_id (FK, indexed), role, content, refused, created_at | `refused` flags the fixed-string refusal path for analytics |
| `citations` | id (PK), message_id (FK, indexed), chunk_id (FK, indexed), document_id (FK), document_title, snippet, rank | Its own table (not JSON on `messages`) so citation frequency is queryable per document |

Full column definitions and constraints: `backend/app/db/models.py`.
Migration: `backend/alembic/versions/0001_initial_schema.py`.

## 5. API Surface

All routes versioned under `/api/v1`, all require the `X-API-Key` header,
all documented live at `/docs` (OpenAPI, auto-generated from the Pydantic
models — never hand-edited, always accurate).

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/documents` | Upload + fully ingest one file |
| GET | `/api/v1/documents` | List documents with chunk counts (admin view) |
| POST | `/api/v1/documents/{id}/reindex` | Re-parse/chunk/embed one document |
| POST | `/api/v1/documents/reindex-all` | Re-index every document with a file still on disk |
| DELETE | `/api/v1/documents/{id}` | Remove a document, its chunks, and its vectors |
| POST | `/api/v1/chat/stream` | SSE stream: tokens, citations, then a `done` event |
| GET | `/api/v1/chat/conversations/{id}` | Full history for a conversation |
| GET | `/api/v1/health` | Liveness check |

Every error path returns a real HTTP status code with
`{"error": {"code": ..., "message": ...}}` — never a 200 with an error
disguised in the body (see `app/core/errors.py`).

## 6. Security

- API-key authentication on every route (`X-API-Key` header, checked in
  `app/core/security.py`). Upgrade path documented inline: swap this
  dependency for Entra ID OAuth2 without touching route handlers.
- Confidential data classification: this pilot's corpus is fictional, but
  the ingestion pipeline never sends raw files anywhere except the
  configured embeddings/generation endpoint — no third-party analytics,
  no client-side storage of document content beyond the current session.
- Prompt injection guardrails (functional requirement — see
  `app/services/guardrails.py`): a hardened system prompt that explicitly
  refuses to treat retrieved content or user text as instructions, plus a
  pattern-matching pre-filter that flags common injection phrasing for
  logging/demo purposes.
- Secrets (`API_KEY`, Azure/DeepSeek/Anthropic keys) live only in `.env`,
  loaded via `pydantic-settings`; never committed, never logged.

## 7. Design Decisions You Must Defend

### 7.1 Chunking

**Choice:** structure-aware splitting on document headings/pages first,
then a fixed ~350-token window with 60-token overlap within each section
(see `app/services/chunking.py` docstring for the full reasoning).

**Rejected alternative 1 — whole-document embedding (one vector per
document).** Rejected because a single question ("what's the PTO
rollover cap?") would retrieve the entire 4-section PTO policy instead of
the one relevant paragraph, wasting context budget and diluting the
embedding's specificity.

**Rejected alternative 2 — fixed-size chunking with no structure
awareness (e.g. naive 500-character sliding window over raw text).**
Rejected because it can split a table row or a heading from its own body
text, producing chunks like "...as shown below:" with no antecedent —
exactly the kind of context-free fragment that produces confidently wrong
answers.

### 7.2 Retrieval

**Choice:** hybrid (vector + keyword) via Azure AI Search in production;
a cosine-similarity + keyword-overlap approximation locally for dev
parity.

**Rejected alternative 1 — pure vector search.** Under-weights exact-term
queries: "What is the EAP phone number?" needs the literal digits, which
embeddings alone don't reliably prioritize over semantically similar but
numerically wrong chunks.

**Rejected alternative 2 — pure keyword (BM25) search.** Misses
paraphrased questions ("time off I've banked" vs. the document's "PTO
balance") that don't share vocabulary with the source text.

*[Fill in what you actually measured: run your 5–10 test questions
against pure-vector, pure-keyword, and hybrid, and record which mode got
the correct top-1 source for each.]*

### 7.3 Top-k and context assembly

Top-k = 5 by default (`TOP_K` in `.env`). Ordered by retrieval score, not
recency or alphabetical. Deduplicated by `chunk_id` (hybrid search can
return the same chunk via both its vector and keyword match). See
`app/services/retrieval.py` docstring for the full token-budget math.

### 7.4 Model choice

*[Fill in after running the comparison — see Section 9 for a cost
starting point. Record: which model answered the 5–10 test questions
correctly, average latency to first token, and cost per 1,000 queries for
each provider you tested.]*

### 7.5 Conversation history placement

History lives in the relational database (`messages` table), not
client-side and not in server memory — a conversation survives a backend
restart. Only the last 8 messages (4 turns) are sent into each prompt
(`app/data_access/chat_repo.py::recent_history`), bounding token cost
regardless of how long a conversation runs; policy Q&A rarely depends on
context older than that.

## 8. Retrieval Quality Note

*[Replace with your actual run output.]*

| # | Question | Expected source | Actual top-1 source | Score | Notes |
|---|---|---|---|---|---|
| 1 | How many PTO days do employees accrue per month? | Paid Time Off Policy | | | |
| 2 | How long is paid parental leave for a birthing parent? | Parental Leave Policy | | | |
| 3 | What's the company match on the 401(k)? | 401(k) Retirement Plan Summary | | | |
| 4 | What's the meal reimbursement limit for dinner? | Expense Reimbursement Policy | | | |
| 5 | How many free EAP counseling sessions do I get? | EAP Guide | | | |
| 6 | What's Contoso's stock ticker? | *(none — should refuse)* | | | |
| 7 | *[your question]* | | | | |
| 8 | *[your question]* | | | | |

What you tuned: *[e.g. "raised MIN_RELEVANCE_SCORE from 0.15 to 0.18 after
question 6 initially retrieved the Employee Handbook Introduction with a
borderline score instead of refusing"]*

## 9. Cost Estimate

Pricing changes frequently — verify current numbers against your Azure
OpenAI / DeepSeek pricing page before submitting; the structure below is
what to fill in, not final numbers.

**Assumptions to state explicitly:** average question ≈ 30 tokens,
average retrieved context ≈ 1,500 tokens (5 chunks × ~300 tokens), average
answer ≈ 200 tokens → roughly 1,730 input + 200 output tokens per query.

| Scale | Users | Queries/user/day | Queries/month | Est. LLM cost/month | Est. Azure AI Search tier | Est. total/month |
|---|---|---|---|---|---|---|
| Pilot | 100 | 3 | ~9,000 | *[queries × (input tokens × input $/token + output tokens × output $/token)]* | Free or Basic | *[sum]* |
| Production | 5,000 | 3 | ~450,000 | *[same formula × 50]* | Standard S1 (needs the higher query-per-second ceiling) | *[sum]* |

Show your actual math here, not just the table — e.g.:
```
9,000 queries × 1,730 input tokens = 15,570,000 input tokens
9,000 queries × 200 output tokens  =  1,800,000 output tokens
Input cost:  15.57M tokens × $[X]/1M = $[Y]
Output cost:  1.80M tokens × $[X]/1M = $[Y]
```

## 10. Scalability — What Changes at 100x Load

At 100x the pilot's traffic (100 → 10,000 concurrent-ish users):

- **What breaks first:** SQLite. It's fine for a single-process pilot but
  has no real concurrent-write story. Move `DATABASE_URL` to Azure
  Database for PostgreSQL — no application code changes required, only
  the connection string and running `alembic upgrade head` against it.
- **Vector store:** the local numpy store (fine for dev) would be far too
  slow and memory-bound at this scale; Azure AI Search's Standard tier
  scales replicas/partitions independently of the app tier and is the
  production default for exactly this reason.
- **Stateless API processes:** `app/main.py` holds no in-memory
  conversation state — every request reads/writes through the database,
  so the FastAPI process can be horizontally scaled behind a load
  balancer (Azure Container Apps with autoscale rules on concurrent
  requests) without sticky sessions.
- **Async I/O:** every LLM, embeddings, and Azure Search call in this
  codebase is `async`/`await` (`httpx.AsyncClient`) — a single process can
  hold many in-flight requests without blocking on network I/O, which
  matters most for the slow leg of every request (the LLM call).
- **Background jobs:** document ingestion currently runs synchronously
  inside the upload request. At 100x scale (large batch re-indexing,
  frequent document updates), move `ingest_file`/`reindex_document` onto
  a queue (Azure Storage Queue + a worker, or Azure Functions) so a large
  PDF doesn't hold an HTTP request open for tens of seconds.
- **Caching:** repeated questions (e.g. "what's the PTO policy") are
  extremely common in an internal chatbot. Add a cache keyed on the
  normalized query (or its embedding) in front of the LLM call — Azure
  Cache for Redis — to cut both latency and token cost for the long tail
  of near-duplicate questions.
- **Rate limiting:** add per-user or per-API-key rate limits before this
  goes past pilot, to bound worst-case cost from a runaway client or
  accidental retry loop.

## 11. Pattern Justification Summary

See Section 7 above for chunking and retrieval; the same "state the
choice, name 2 rejected alternatives, give the specific reason" structure
applies to every major decision in this document.
