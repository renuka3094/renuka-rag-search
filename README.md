# Contoso Knowledge Assistant — RAG Knowledge Chatbot

**Author:** Renuka Jagadale
**Program:** DataFactZ AI Engineering Internship — Week 1, Use Case 1

An internal knowledge assistant for Contoso Corp employees: natural-
language questions about company policy, answered only from an indexed
document corpus, with citations, and an honest refusal for anything
outside that corpus.

## Documentation

| Doc | Contents |
|---|---|
| [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) | Running the backend, frontend, and corpus generation locally |
| [`docs/AZURE_SETUP.md`](docs/AZURE_SETUP.md) | Provisioning the Azure AI Foundry, AI Search, and PostgreSQL resources |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | The deployed architecture on Azure — App Service, Static Web Apps, GitHub Actions CI/CD |
| [`docs/DESIGN_DOC.md`](docs/DESIGN_DOC.md) | Solution design: architecture, data flow, database ERD, pattern justification, scalability |

## Project layout

```
backend/     FastAPI app — routers → services → data access, SQLAlchemy +
             Alembic, chunking/retrieval/generation/guardrail services
frontend/    Vite + React — branded chat UI and admin view
corpus/      generate_corpus.py + 20 generated Contoso Corp documents
             (5 markdown, 5 html, 5 docx, 5 pdf)
docs/        setup guide, Azure setup, deployment record, design doc
```

## Quick start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # see docs/AZURE_SETUP.md for the values
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Corpus (new terminal)
cd corpus && python generate_corpus.py

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env        # set VITE_API_KEY to match backend's API_KEY
npm run dev
```

Open `http://localhost:5173`, upload the generated corpus documents from
the Knowledge Base page, and ask a question in Chat.

Live deployment: see `docs/DEPLOYMENT.md` for URLs and architecture.
