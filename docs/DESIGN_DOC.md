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
- **Frontend (React + Vite):** Chat page (multi-turn, streaming, model
  switcher, citation pills, a chat-history sidebar backed by the
  `conversations` table) and Admin page (document list, chunk counts,
  re-index all, usage analytics). There's deliberately no upload or
  delete action in the Admin UI — I treat the knowledge base as a fixed
  corpus (`corpus/generate_corpus.py`), so adding or removing a document
  is a corpus-generation + one-off ingestion-script step, not something
  exposed to whoever has the shared API key. Shared layout shell reused
  across all three Week apps.
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
  code change. I exposed this directly in the product, not just in
  config: the Chat page has a live model dropdown (GPT-5.5 / DeepSeek-
  V3.2, both served through the same shared Azure AI Foundry project)
  that lets me generate a like-for-like answer from either model on the
  same question without redeploying anything (Section 7.4). Embeddings
  run on Azure (`azure_v1` mode) — DeepSeek doesn't currently expose a
  public embeddings endpoint, so it's generation-only.

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

1. A new document enters the knowledge base by regenerating the corpus
   (`corpus/generate_corpus.py`) and running it through `ingest_file()`
   via a one-off script: parse (format-specific) → chunk (structure-
   aware, token-bounded) → embed (batch call) → upsert into the vector
   store → persist `Document` + `Chunk` rows. This is intentionally not
   an Admin-UI action — I removed the upload and delete endpoints once I
   settled on treating the corpus as fixed, so nobody with just the
   shared API key can add or remove what's indexed.
2. Employee sends a chat message → backend embeds the query → vector
   store hybrid search returns top-k chunks → **refusal check**: if the
   top score is below threshold, return the fixed refusal string without
   calling the LLM → otherwise assemble a numbered context block, call
   the LLM with the hardened system prompt, stream tokens back over SSE →
   once the full answer is in, filter the retrieved chunks down to just
   the ones the model actually cited (its own `[n]` markers) → persist
   the assistant `Message` + only those `Citation` rows.
3. Admin can re-index a document (e.g. after regenerating the corpus with
   updated content) without touching any other document's index entries,
   or re-index everything at once from the Admin page.

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
| `conversations` | id (PK), title, created_at | `title` defaults to "New conversation" and is set from the employee's first message the moment they send it — this is what powers the chat-history sidebar |
| `messages` | id (PK), conversation_id (FK, indexed), role, content, refused, model, prompt_tokens, completion_tokens, created_at | `refused` flags the fixed-string refusal path for analytics; `model`/token counts are set on assistant messages only, for the usage analytics view |
| `citations` | id (PK), message_id (FK, indexed), chunk_id (FK, indexed), document_id (FK), document_title, snippet, rank | Its own table (not JSON on `messages`) so citation frequency is queryable per document. Only the chunks the model actually cited in its answer get a row here — not every chunk retrieved |

Full column definitions and constraints: `backend/app/db/models.py`.
Migrations: `backend/alembic/versions/0001_initial_schema.py` (initial
schema), `0002_message_model_and_tokens.py` (added `model`,
`prompt_tokens`, `completion_tokens` to `messages` for usage analytics).

## 5. API Surface

All routes versioned under `/api/v1`, all require the `X-API-Key` header,
all documented live at `/docs` (OpenAPI, auto-generated from the Pydantic
models — never hand-edited, always accurate).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/documents` | List documents with chunk counts (admin view) |
| POST | `/api/v1/documents/{id}/reindex` | Re-parse/chunk/embed one document |
| POST | `/api/v1/documents/reindex-all` | Re-index every document with a file still on disk |
| POST | `/api/v1/chat/stream` | SSE stream: tokens, then citations (filtered to what the model actually cited), then a `done` event |
| GET | `/api/v1/chat/conversations` | List conversations (id, title, created_at), newest first — the sidebar's data source |
| GET | `/api/v1/chat/conversations/{id}` | Full history for a conversation |
| DELETE | `/api/v1/chat/conversations/{id}` | Delete a conversation and its messages/citations (cascades) |
| GET | `/api/v1/chat/analytics` | Usage analytics (questions, tokens, per-model breakdown) for the Admin page |
| GET | `/api/v1/health` | Liveness check |

There's no upload or delete route under `/api/v1/documents` — see
Section 3 for why.

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

### 7.3 Top-k, context assembly, and what gets shown as a citation

Top-k = 5 by default (`TOP_K` in `.env`). Ordered by retrieval score, not
recency or alphabetical. Deduplicated by `chunk_id` (hybrid search can
return the same chunk via both its vector and keyword match). See
`app/services/retrieval.py` docstring for the full token-budget math.

All 5 retrieved chunks go into the LLM's context every time, but I don't
show all 5 as "sources" in the UI — I originally did, and it meant a
narrow question like "how many PTO days do I accrue" showed the same
5-source pill as a broad one like "what benefits are offered," which
didn't actually reflect what the answer drew on. The system prompt
already requires the model to cite `[n]` markers for every factual claim
(see `app/services/guardrails.py`), so I parse those markers out of the
finished answer and only persist/display the citations whose rank was
actually referenced (`extract_cited_ranks()` in
`app/services/guardrails.py`). If the model doesn't cite anything at all
— a formatting slip rather than the normal case — I fall back to showing
everything retrieved rather than silently hiding sources. In practice
this means citation counts now vary genuinely by question: 1 source for
a narrow factual question, up to all 5 for a broad one.

### 7.4 Model choice

Production runs on `gpt-5.5` via the shared Azure AI Foundry project
(`azure_v1` provider mode). I also wired DeepSeek-V3.2 into the same
Foundry connection and exposed both as a live dropdown on the Chat page,
so the "compare at least two generation options" requirement is
something I can actually demo on the same question live, not just narrate
from config. One real issue surfaced doing this: DeepSeek's responses
were being blocked by Azure's content filter (`JailbreakBlockList`)
because my hardened system prompt literally quoted example jailbreak
phrases ("ignore your instructions...") as part of describing what to
refuse — the filter was reacting to the system prompt's own wording, not
anything the employee typed. I reworded those rules to describe the
behavior without quoting attack phrasing, verified both providers still
refuse actual injection attempts correctly, and confirmed no regression
in the existing test suite. Latency/cost-per-1,000-queries numbers
across the two providers are still pending a dedicated run.

### 7.5 Conversation history placement

History lives in the relational database (`messages` table), not
client-side and not in server memory — a conversation survives a backend
restart. Only the last 8 messages (4 turns) are sent into each prompt
(`app/data_access/chat_repo.py::recent_history`), bounding token cost
regardless of how long a conversation runs; policy Q&A rarely depends on
context older than that.

## 8. Retrieval Quality Note

Run against the corpus as it stood at the time — 20 documents, 139
chunks — in production, via `azure_v1` (`gpt-5.5`). The corpus has since
grown to 24 documents / 168 chunks, the Paid Time Off Policy's Accrual
section changed from a flat 1.5-days/month rate to tenure-based tiers,
and citation display now filters to only what the model actually cited
(Section 7.3) — none of that changes the retrieval-quality findings
below, but the specific PTO figures quoted in Q1's notes reflect the
corpus as it was on this test date, not the current wording.

| # | Question | Expected source | Actual top-1 source | Correct? | Notes |
|---|---|---|---|---|---|
| 1 | How many PTO days do employees accrue per month? | Paid Time Off Policy | Paid Time Off Policy | ✓ | Exact figure (1.5/month, 18/year), correctly cited |
| 2 | What percentage of my health insurance premium does the company cover? | Health Insurance Benefits Guide | Health Insurance Benefits Guide | ✓ | Correct 80%/60% split, correctly cited |
| 3 | How much is the referral bonus for a hard-to-fill engineering role? | Employee Referral Program | Employee Referral Program | ✓ | Correct $3,000 figure, correctly cited |
| 4 | What happens if my laptop hasn't arrived by my start date? | Onboarding Checklist for New Hires | Onboarding Checklist for New Hires | ✓ | Correctly surfaced FAQ-section content specifically, not just the parent document |
| 5 | How many vacation days do I earn each month? *(paraphrase of Q1 — "vacation" vs. "PTO", "earn" vs. "accrue")* | Paid Time Off Policy | Paid Time Off Policy | ✓ | Confirms hybrid search handles vocabulary mismatch, not just exact keyword overlap |
| 6 | Can I carry over unused time off into next year? | Paid Time Off Policy (Rollover) | Paid Time Off Policy | ✓ | Correct 5-day rollover cap and Dec 31 forfeiture date |
| 7 | What counts as a full-time employee at Contoso Corp? | Employee Handbook Introduction (Key Definitions) | Employee Handbook Introduction | ✗ | **Retrieval miss** — see note below |
| 8 | What's Contoso Corp's stock ticker symbol? | *(none — should refuse)* | *(refused)* | ✓ | Correctly refused, but see note below on *how* |

**6 of 8 fully correct.** Two results are genuinely informative rather
than simple failures:

- **Q7** correctly identified the right *document* (Employee Handbook
  Introduction) but the wrong *chunk* within it — it retrieved the "Who
  This Applies To" section (which also mentions "full-time" prominently)
  instead of the "Key Definitions" section that actually contains the
  precise definition. This is a real, useful finding: document-level
  retrieval can succeed while chunk-level retrieval still misses the
  specific passage that answers the question, especially once a document
  has many sections competing for the same keywords.
- **Q8** refused correctly, but not for the reason the design assumes.
  Checking the raw citations showed retrieval still returned 5 chunks
  (irrelevant ones — a 401(k) FAQ, Code of Conduct sections) with scores
  above the 0.01 Azure threshold, so `should_refuse()`'s score gate did
  *not* trigger. The refusal instead came from the LLM itself, following
  the system prompt's rule to refuse when the retrieved context doesn't
  answer the question. In practice, this means the score-based gate
  rarely fires at all against Azure AI Search — Reciprocal Rank Fusion
  scores for *any* returned hit are almost always above 0.01, so the
  system prompt's own honesty rule is doing the real refusal work, not
  the code-level threshold.

**What was tuned:** the refusal threshold, `MIN_RELEVANCE_SCORE`, had been
a single value (0.18) calibrated against the local vector store's
cosine-similarity scores. Once deployed against Azure AI Search, every
query was refused regardless of relevance — Azure's hybrid search scores
results via Reciprocal Rank Fusion, a much smaller scale (typically
0.01–0.03), so the 0.18 threshold was never met. Split the constant into
`MIN_RELEVANCE_SCORE_LOCAL` (0.18) and `MIN_RELEVANCE_SCORE_AZURE` (0.01),
selected by `settings.vector_backend`, in `app/services/retrieval.py`.
Q8 above suggests this threshold could be raised further for the Azure
path — a natural next tuning step, not yet done.

## 9. Cost Estimate

**Assumptions:** average question ≈ 30 tokens,
average retrieved context ≈ 1,500 tokens (5 chunks × ~300 tokens), average
answer ≈ 200 tokens → roughly 1,730 input + 200 output tokens per query,
plus one embedding call per query (the question itself, ~30 tokens) for
retrieval.

**Pricing used** (Azure OpenAI Global Standard list pricing, July 2026):
`gpt-5.5` at $5/1M input tokens and $30/1M output tokens;
`text-embedding-3-small` at $0.02/1M tokens. Azure AI Search: Free tier
(no cost, sufficient for this corpus's size) for the pilot; Standard S1
at $245.28/month per search unit for production. These are public list
prices, not the shared Foundry project's actual negotiated/internal rate
— I don't have visibility into that from this pilot, so treat this as a
directional estimate, not a bill.

| Scale | Users | Queries/user/day | Queries/month | Est. LLM + embedding cost/month | Est. Azure AI Search tier | Est. total/month |
|---|---|---|---|---|---|---|
| Pilot | 100 | 3 | ~9,000 | ~$132 | Free (corpus is only 168 chunks — well within the Free tier's limits) | **~$132/month** |
| Production | 5,000 | 3 | ~450,000 | ~$6,593 | Standard S1 × 2 replicas for HA — ~$491/month | **~$7,084/month** |

```
Pilot — 9,000 queries/month:
  Input:      9,000 × 1,730 tokens = 15,570,000 tokens (15.57M) × $5/1M  = $77.85
  Output:     9,000 ×   200 tokens =  1,800,000 tokens ( 1.80M) × $30/1M = $54.00
  Embeddings: 9,000 ×    30 tokens =    270,000 tokens ( 0.27M) × $0.02/1M = $0.01
  LLM + embedding subtotal: ~$131.86/month
  + Azure AI Search Free tier: $0
  = ~$132/month

Production — 450,000 queries/month (50× pilot volume):
  Input:      450,000 × 1,730 tokens = 778,500,000 tokens (778.5M) × $5/1M  = $3,892.50
  Output:     450,000 ×   200 tokens =  90,000,000 tokens ( 90.0M) × $30/1M = $2,700.00
  Embeddings: 450,000 ×    30 tokens =  13,500,000 tokens ( 13.5M) × $0.02/1M = $0.27
  LLM + embedding subtotal: ~$6,592.77/month
  + Azure AI Search Standard S1 × 2 (recommended for HA, not just 1 unit): ~$490.56/month
  = ~$7,083/month
```

I priced Standard S1 at 2 replicas for production rather than 1, since a
single search unit has no failover — losing it would take the whole
retrieval path down, which isn't acceptable once this is past a pilot. A
single S1 unit (no HA) would bring production down to roughly
$6,838/month instead. Either way, the LLM generation cost dominates the
total by a wide margin at both scales — Azure AI Search is a rounding
error next to it — so if cost ever needs to come down, token volume per
query (top-k, context size, answer length) is the lever that actually
matters, not the vector store tier.

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
- **Background jobs:** ingestion (via the one-off script) and re-indexing
  (via the Admin API) both run synchronously today. At 100x scale (large
  batch re-indexing, frequent document updates), move
  `ingest_file`/`reindex_document` onto a queue (Azure Storage Queue + a
  worker, or Azure Functions) so a large PDF doesn't hold an HTTP request
  open for tens of seconds.
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
