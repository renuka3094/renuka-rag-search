# Solution Design Document — Contoso Knowledge Assistant (RAG Chatbot)

**Program:** DataFactZ AI Engineering Internship — Week 1, Use Case 1
**Author:** Renuka Jagadale
**Date:** July 2026

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
- **Relational database:** SQLite for local development; Azure Database
  for PostgreSQL in production. The application code needs no changes to
  move between them (`app/db/session.py` already branches only on the
  SQLite prefix), but the deployment does need the matching driver —
  `psycopg[binary]`, not `psycopg2-binary` (see Section 2.1) — and a
  `postgresql+psycopg://` connection string.
- **Vector store:** Azure AI Search (hybrid vector + keyword) in
  production; a local numpy cosine-similarity store for zero-cost dev,
  selected by `VECTOR_BACKEND`.
- **LLM providers:** the codebase implements a common streaming interface
  across Azure OpenAI, Azure AI Foundry, DeepSeek, and Claude for
  generation, so switching providers is a configuration change, not a
  code change. Embeddings run on Azure (`azure_v1` mode) — DeepSeek
  doesn't currently expose a public embeddings endpoint, so it's only
  used for generation-side comparison (Section 7.4).

### 2.1 Deployment topology

The diagram above shows the application's internal architecture; this is
where each piece actually runs in Azure. Full as-built record, including
every bug hit while deploying and how each was fixed:
**`docs/DEPLOYMENT.md`**.

| Component | Azure resource | Notes |
|---|---|---|
| Frontend | Static Web App (Free tier) | Built via Vite (`npm run build` → `dist/`), deployed via GitHub Actions on every push to `main` |
| Backend | App Service, Linux, Python 3.11 (Free F1) | `gunicorn` + `uvicorn` workers; deployed via GitHub Actions, server-side Oryx build |
| Relational DB | Azure Database for PostgreSQL, flexible server (Burstable B1ms) | `psycopg` (v3) driver — `psycopg2-binary` failed to install in Azure's Linux build image |
| Vector store | Azure AI Search (hybrid vector + keyword) | Index `contoso-kb`, created automatically on first ingestion |
| LLM + embeddings | Shared Azure AI Foundry project | `azure_v1` provider mode; chat model `gpt-5.5`, embeddings `text-embedding-3-small` |
| CI/CD | GitHub Actions (2 workflows) | One per hosting resource, both triggered by push to `main` |

Secrets live in exactly two places: local `.env` files (gitignored, never
committed) and each Azure resource's own server-side configuration —
never in a repo file or a workflow YAML as literal text.

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
- Secrets (`API_KEY`, Azure/DeepSeek/Anthropic keys) live only in local
  `.env` files (loaded via `pydantic-settings`) and, in the deployed
  environment, in the Azure App Service's own application settings —
  never committed to git, never logged, never present in a GitHub
  Actions workflow file as literal text (see `docs/DEPLOYMENT.md` for the
  full secrets map).

## 7. Design Decisions

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

*Status: comparative measurement against pure-vector-only and
pure-keyword-only modes is pending — planned as part of the retrieval
quality run in Section 8.*

### 7.3 Top-k and context assembly

Top-k = 5 by default (`TOP_K` in `.env`). Ordered by retrieval score, not
recency or alphabetical. Deduplicated by `chunk_id` (hybrid search can
return the same chunk via both its vector and keyword match). See
`app/services/retrieval.py` docstring for the full token-budget math.

### 7.4 Model choice

Production runs on `gpt-5.5` via the shared Azure AI Foundry project
(`azure_v1` provider mode). A second-provider comparison against DeepSeek
(already wired up via `GENERATION_PROVIDER=deepseek`) is planned to
satisfy the "compare at least two options" requirement — latency,
quality on the test question set, and cost per 1,000 queries to be
recorded once that run is complete.

### 7.5 Conversation history placement

History lives in the relational database (`messages` table), not
client-side and not in server memory — a conversation survives a backend
restart. Only the last 8 messages (4 turns) are sent into each prompt
(`app/data_access/chat_repo.py::recent_history`), bounding token cost
regardless of how long a conversation runs; policy Q&A rarely depends on
context older than that.

## 8. Retrieval Quality Note

*Status: full 5–10 question run against the complete 20-document corpus
pending — table below to be completed from that run.*

| # | Question | Expected source | Actual top-1 source | Score | Notes |
|---|---|---|---|---|---|
| 1 | How many PTO days do employees accrue per month? | Paid Time Off Policy | | | |
| 2 | How long is paid parental leave for a birthing parent? | Parental Leave Policy | | | |
| 3 | What's the company match on the 401(k)? | 401(k) Retirement Plan Summary | | | |
| 4 | What's the meal reimbursement limit for dinner? | Expense Reimbursement Policy | | | |
| 5 | How many free EAP counseling sessions do I get? | EAP Guide | | | |
| 6 | What's Contoso's stock ticker? | *(none — should refuse)* | | | |
| 7 | What are the core hours for remote employees? | Remote Work Policy | Remote Work Policy | ✓ | Correctly cited, verified in production |
| 8 | What equipment is provided for remote work? | Remote Work Policy | Remote Work Policy | ✓ | Correct follow-up answer, multi-turn context retained |

**What was tuned:** the refusal threshold, `MIN_RELEVANCE_SCORE`, had been
a single value (0.18) calibrated against the local vector store's
cosine-similarity scores. Once deployed against Azure AI Search, every
query was refused regardless of relevance — Azure's hybrid search scores
results via Reciprocal Rank Fusion, a much smaller scale (typically
0.01–0.03), so the 0.18 threshold was never met. Split the constant into
`MIN_RELEVANCE_SCORE_LOCAL` (0.18) and `MIN_RELEVANCE_SCORE_AZURE` (0.01),
selected by `settings.vector_backend`, in `app/services/retrieval.py`.

## 9. Cost Estimate

**Assumptions:** average question ≈ 30 tokens,
average retrieved context ≈ 1,500 tokens (5 chunks × ~300 tokens), average
answer ≈ 200 tokens → roughly 1,730 input + 200 output tokens per query.

| Scale | Users | Queries/user/day | Queries/month | Est. LLM cost/month | Est. Azure AI Search tier | Est. total/month |
|---|---|---|---|---|---|---|
| Pilot | 100 | 3 | ~9,000 | *pending — current pricing to confirm* | Free or Basic | *pending* |
| Production | 5,000 | 3 | ~450,000 | *pending (~50× pilot volume)* | Standard S1 (higher query-per-second ceiling) | *pending* |

```
9,000 queries × 1,730 input tokens = 15,570,000 input tokens
9,000 queries × 200 output tokens  =  1,800,000 output tokens
Input cost:  15.57M tokens × current per-token rate
Output cost:  1.80M tokens × current per-token rate
```

Final figures depend on the shared Foundry project's billing rate for
`gpt-5.5`, which is being confirmed before this section is finalized —
placeholder math above uses the token-volume assumptions already stated.

## 10. Scalability — What Changes at 100x Load

At 100x the pilot's traffic (100 → 10,000 concurrent-ish users):

- **What breaks first:** the database's compute tier. Production already
  runs on Azure Database for PostgreSQL rather than SQLite (SQLite is
  local-dev-only, given App Service's local disk doesn't reliably persist
  across restarts). At 100x load, the current Burstable B1ms tier — sized
  for a pilot — would need to move to a higher, non-burstable compute
  tier with connection pooling (e.g. PgBouncer) in front of it, since a
  single small instance has a hard ceiling on concurrent connections
  regardless of query complexity.
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

Five decisions carry the most architectural weight in this system, all
detailed with rejected alternatives in Section 7: structure-aware
chunking over whole-document or naive fixed-size splitting; hybrid
vector+keyword retrieval over pure-vector or pure-keyword search; a
five-chunk, score-ordered, deduplicated context window; a
multi-provider LLM abstraction that keeps model choice a configuration
decision rather than a code dependency; and database-backed (not
in-memory) conversation history, bounded to the last four turns per
prompt. Each reflects the same underlying constraint — this system has to
be defensible in front of a client, not just functional in a demo.
