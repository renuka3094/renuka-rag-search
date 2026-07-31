# Deployment Architecture

**Author:** Renuka Jagadale
**Project:** Contoso Knowledge Assistant — RAG Knowledge Chatbot (Use Case 1)

## Overview

The application runs on three managed Azure resources, wired together
with GitHub Actions for continuous deployment. The frontend and backend
each deploy independently on every push to `main`; the database and the
AI resources (Azure AI Search, Azure AI Foundry) are provisioned
separately and referenced by the backend through environment
configuration.

```
                         GitHub — renuka3094/renuka-rag-search
                         ├─ .github/workflows/main_renuka-rag-backend.yml
                         └─ .github/workflows/azure-static-web-apps-*.yml
                                 │ push to main → GitHub Actions
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌──────────────────────┐   ┌───────────────────────────┐
        │ Azure Static Web App  │   │ Azure App Service (Linux) │
        │ (see App Service /    │──▶│ (see App Service /        │
        │ Static Web App        │   │ Python 3.11, gunicorn +   │
        │ resource in portal)   │   │ uvicorn workers           │
        └──────────────────────┘   └──────────┬────────────────┘
                                                │
                        ┌───────────────────────┼───────────────────────┐
                        ▼                       ▼                       ▼
          ┌─────────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
          │ Azure Database for      │ │ Azure AI Search        │ │ Azure AI Foundry      │
          │ PostgreSQL Flexible     │ │ (see resource in       │ │ (shared project)      │
          │ Server                  │ │ portal)                │ │ azure_v1 endpoint     │
          │ (see resource in       │ │ index: contoso-kb      │ │ chat: gpt-5.5         │
          │ portal)                 │ │ hybrid vector+keyword  │ │ embeddings:           │
          └─────────────────────────┘ └──────────────────────┘ │ text-embedding-3-small│
                                                                 └──────────────────────┘
```

**Live endpoints**
- Frontend and backend URLs are available in the Azure Portal (Static Web
  App / App Service overview pages) and in each GitHub Actions workflow
  run, and are intentionally not published here.
- Backend health check: `/api/v1/health`

## Source control

The repository is gitignored for all `.env` files, the local SQLite/vector
store data directory, and both language-specific dependency folders
(`backend/.venv/`, `frontend/node_modules/`) before the first commit, so
no credential has ever entered git history. Real secrets live only in two
places: local `.env` files, and each Azure resource's own server-side
configuration. Neither GitHub Actions workflow references a secret as
literal text — both read from encrypted GitHub Actions secrets.

## Database — Azure Database for PostgreSQL

A flexible server on the Burstable B1ms tier, using the server's default
`postgres` database rather than a dedicated one. PostgreSQL authentication
with a firewall scoped to the App Service's outbound traffic plus my own
IP for running migrations.

The driver required one correction after the initial attempt:
`psycopg2-binary` does not install cleanly in Azure App Service's Linux
build environment (its precompiled wheel isn't compatible with that
container). Switched to `psycopg[binary]` — the modern Psycopg 3 driver —
and updated the connection string's scheme from `postgresql+psycopg2://`
to `postgresql+psycopg://` accordingly. No application code changed:
`app/db/session.py` was already written to branch only on a SQLite prefix
for its `connect_args`, so it worked against Postgres unmodified.

Migrations run via `alembic upgrade head` against the live
`DATABASE_URL`, creating the five tables defined in
`app/db/models.py`.

## Backend — Azure App Service

Linux, Python 3.11, Free tier. Startup command:

```
gunicorn -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000 app.main:app
```

`gunicorn` supervises `uvicorn` worker processes — App Service's process
manager expects this shape for a Python web app rather than a bare
`uvicorn` invocation. All application configuration (`API_KEY`,
`DATABASE_URL`, vector store and model provider settings, `CORS_ORIGINS`)
is set as App Service application settings, mirroring `backend/.env`
one-to-one.

Deployed via GitHub Actions, connected through Deployment Center using
basic authentication (the identity-based/OIDC option requires an Azure AD
app registration, which this subscription doesn't grant permission to
create). This generated `.github/workflows/main_renuka-rag-backend.yml`,
which needed three corrections before it reflected the repository's
actual layout and produced a working deployment:

1. **Working directory.** The generated workflow assumed the application
   lived at the repository root; this is a monorepo with `backend/` and
   `frontend/` as siblings. Added `working-directory: backend` to the
   build job and corrected the deploy step's artifact path accordingly.
2. **Build strategy.** The workflow initially built a virtual environment
   inside the GitHub Actions runner and shipped it as part of the deploy
   artifact. That environment didn't match the target container, and the
   app failed at startup with `ModuleNotFoundError: No module named
   'psycopg2'`. Removed the local build step entirely — Azure's own Oryx
   build engine (`SCM_DO_BUILD_DURING_DEPLOYMENT=true`, enabled by default
   for this integration) installs `requirements.txt` server-side, inside
   the container the app actually runs in, which is the correct place for
   that to happen.
3. **Driver compatibility.** Even Oryx's own server-side build failed to
   install `psycopg2-binary` — resolved by moving to `psycopg[binary]` as
   described above.

## Frontend — Azure Static Web Apps

Free tier, deployed from the same repository, `/frontend` as the app
location, `dist` as the build output (Vite's actual output directory —
the platform's default suggestion of `build` is the Create React App
convention and doesn't apply here).

Three corrections to the generated workflow and build configuration:

1. **Output path.** Corrected `output_location` from `build` to `dist`.
2. **Build-time configuration.** `VITE_API_BASE_URL` and `VITE_API_KEY`
   are compiled into the JavaScript bundle at build time by Vite, so they
   have to be available while the GitHub Actions workflow runs `npm run
   build`, not afterward. Added both as encrypted GitHub repository
   secrets and referenced them in the workflow's build step via `env:`.
   `VITE_API_KEY` is not treated as confidential once built — it's
   readable in the browser by design, since it ships inside public JS —
   it functions purely as the shared header value the backend checks for,
   matching the intent documented in `app/core/security.py`.
3. **Build environment.** Two related Node/Rollup issues surfaced only in
   Azure's Linux build container:
   - A `package-lock.json` generated on Windows didn't correctly resolve
     the Linux-specific native Rollup binary (a known npm
     optional-dependency resolution issue across platforms). Removed the
     lock file so the Linux build resolves its own platform-correct
     dependencies.
   - The freshly-resolved Rollup binary required a newer `glibc` than the
     build container provides. Pinned an older, compatible Rollup release
     via `overrides` in `frontend/package.json`:
     ```json
     "overrides": { "rollup": "4.24.0" }
     ```

`CORS_ORIGINS` on the backend is set to the frontend's exact URL, no
trailing slash.

## Two issues found after deployment

**Retrieval refusing every question, including in-corpus ones.**
`MIN_RELEVANCE_SCORE` had been tuned against the local vector store's
cosine-similarity scores (0–1 range). In production, Azure AI Search's
hybrid search scores results via Reciprocal Rank Fusion, on a much
smaller scale (typically 0.01–0.03) — every retrieved chunk's score fell
below the threshold, so the app refused unconditionally regardless of
relevance. Confirmed by inspecting the Azure AI Search index directly
(document count, raw stored documents via Search Explorer) to rule out an
ingestion failure, then instrumenting `retrieve()` with temporary logging
to inspect actual hit counts and scores. Fixed in
`app/services/retrieval.py` by splitting the threshold into
`MIN_RELEVANCE_SCORE_LOCAL` and `MIN_RELEVANCE_SCORE_AZURE`, selected by
`settings.vector_backend`.

**Page titles rendering invisible.** `tokens.css` defaults to a dark
theme at `:root`, switching to light only within elements carrying the
`.theme-auto` class (applied to `.app-shell`). `global.css` set the
page's base text color on `body`, which sits above `.app-shell` in the
DOM — so that declaration was always evaluated against the dark-theme
default and never picked up the light override, and its near-white
computed value inherited down to the two `<h1>` elements that don't set
their own color. Fixed by setting `background`/`color` explicitly on
`.app-shell` itself, at the point where `.theme-auto` is actually in
scope.

## Secrets reference

| Secret | Location |
|---|---|
| `API_KEY` | `backend/.env` (local) + App Service application settings |
| `DATABASE_URL` | same |
| `AZURE_SEARCH_API_KEY` | same |
| `AZURE_OPENAI_API_KEY` | same |
| App Service publish credential | GitHub encrypted Actions secret |
| Static Web Apps deployment token | GitHub encrypted Actions secret |
| `VITE_API_BASE_URL` / `VITE_API_KEY` | GitHub encrypted Actions secret → compiled into the public frontend bundle |

No credential appears in a repository file or in a workflow YAML as
literal text.
