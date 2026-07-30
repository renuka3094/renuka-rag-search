# Azure Resource Setup

**Author:** Renuka Jagadale
**Project:** Contoso Knowledge Assistant — RAG Knowledge Chatbot (Use Case 1)

This covers provisioning the three Azure resources this project depends
on, in the shared resource group `AI_Training`: the AI models (generation
+ embeddings), the vector store, and the relational database. All
resources are tagged `owner=renuka` and, where billing is hourly rather
than per-token, stopped or deleted when not actively in use.

## 1. AI models — Azure AI Foundry

Model deployments for this project (`gpt-5.5` for generation,
`text-embedding-3-small` for embeddings) are hosted in a shared AI Foundry
project (`AI_Training_Project`) rather than a resource I provisioned
myself, so this section documents retrieval of the connection details
rather than resource creation:

1. Sign in at `ai.azure.com` and open `AI_Training_Project`.
2. The project's overview page exposes a **Key**, a **Project endpoint**,
   and an **Azure OpenAI endpoint**. This project's code is written
   against the unified `/openai/v1/...` API shape, so the Azure OpenAI
   endpoint is the one in use here.
3. Under **View deployments**, the exact deployment names (`gpt-5.5`,
   `text-embedding-3-small`) are copied verbatim into `.env` — the
   deployment name shown in this table is what the API call needs, not a
   general label for the model family.

Configuration (`backend/.env`):

```
EMBEDDINGS_PROVIDER=azure_v1
GENERATION_PROVIDER=azure_v1
AZURE_OPENAI_ENDPOINT=<Azure OpenAI endpoint from the project overview, ending in /openai/v1>
AZURE_OPENAI_API_KEY=<Key from the project overview>
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.5
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-small
```

`azure_v1` is one of five provider modes this codebase supports
(`app/services/generation.py` / `embeddings.py`); it matches a unified
`/openai/v1` endpoint with bearer-token auth, as opposed to the
classic per-deployment Azure OpenAI URL shape (`azure_openai`) or the
Foundry Models unified endpoint shape (`azure_foundry`).

## 2. Vector store — Azure AI Search

Provisioned directly, since Azure AI Search is the default hybrid
vector/keyword store specified for this use case.

1. Portal → **Azure AI Search** → Create, in `AI_Training`, **Free**
   pricing tier (sufficient for a 20-document corpus — 50MB storage cap,
   3 indexes max).
2. Tag `owner=renuka`.
3. Once deployed, **Keys** page → copy the primary admin key; **Overview**
   page → copy the service URL.

Configuration:

```
VECTOR_BACKEND=azure
AZURE_SEARCH_ENDPOINT=https://renu-embed-vector.search.windows.net
AZURE_SEARCH_API_KEY=<primary admin key>
AZURE_SEARCH_INDEX_NAME=contoso-kb
```

The index itself doesn't need to be created manually — the backend
creates it automatically on first ingestion
(`AzureSearchVectorStore._ensure_index` in
`app/services/vector_store.py`).

**Free tier limits:** 3 indexes, 50MB storage, no semantic ranker — all
within bounds for this corpus. Free tier costs nothing idle, so no
ongoing cost-hygiene action is needed unless upgraded to a paid tier for
testing.

## 3. Relational database — Azure Database for PostgreSQL

The application's relational data (`documents`, `chunks`, `conversations`,
`messages`, `citations`) lives in a flexible-server Postgres instance
rather than the SQLite default, since App Service's local disk doesn't
reliably persist across restarts.

1. Portal → **Azure Database for PostgreSQL flexible server** → Create,
   in `AI_Training`.
2. Workload type: Development. Compute + storage: Burstable, B1ms
   (lowest-cost tier appropriate for this scale).
3. PostgreSQL authentication, with the admin credentials stored only in
   `.env` and App Service configuration — never in the repository.
4. Networking: public access, with "allow public access from Azure
   services" enabled (so the App Service can reach it) and a firewall
   rule scoped to whichever client needs to run migrations directly.
5. Tag `owner=renuka`.

Configuration:

```
DATABASE_URL=postgresql+psycopg://<user>:<password>@renuka-rag-db.postgres.database.azure.com:5432/postgres?sslmode=require
```

Note the `+psycopg` scheme (Psycopg 3) rather than `+psycopg2` —
`psycopg2-binary` failed to install in Azure App Service's Linux build
environment (see `docs/DEPLOYMENT.md`), so this project uses
`psycopg[binary]` in `requirements.txt` instead, and the connection
string's driver name has to match.

Tables are created with:

```bash
cd backend
alembic upgrade head
```

**Cost hygiene:** Burstable tier bills hourly regardless of usage — the
server is stopped (not deleted) when not actively in use, since Postgres
Flexible Server supports pausing compute billing for up to seven days
without losing data.

## 4. Optional — DeepSeek, for the required generation comparison

Not an Azure resource. An API key from DeepSeek's platform
(`platform.deepseek.com`) is enough to run the same corpus and test
questions through a second generation provider for cost/quality
comparison:

```
DEEPSEEK_API_KEY=<key>
GENERATION_PROVIDER=deepseek
```

Embeddings stay on `azure_v1` — DeepSeek does not currently expose a
public embeddings endpoint (documented in `app/services/embeddings.py`).

## Verifying the setup

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: <API_KEY>" \
  -F "file=@../corpus/generated/markdown/remote_work_policy.md"
```

A successful response returns `{"document": {"id": "...", "status":
"indexed", "chunk_count": ...}, ...}`. Failures at this step are almost
always one of: an incorrect `AZURE_OPENAI_*` value or deployment name
mismatch, or — if `VECTOR_BACKEND=azure` — the Search service not yet
fully provisioned, or the key used being a query key rather than the
admin key.
