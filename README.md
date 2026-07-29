#  RAG Knowledge Chatbot — Use Case 1 (Week 1)

**New to Azure/VS Code?** Start with **[docs/SETUP_GUIDE_BEGINNER.md](docs/SETUP_GUIDE_BEGINNER.md)**
— explains portal.azure.com and ai.azure.com navigation from zero, then
every terminal command in order.

Already comfortable with Azure? **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)**
is the faster reference version.

Then: **[docs/DESIGN_DOC.md](docs/DESIGN_DOC.md)** — the design document
draft to fill in with your own measurements before submitting.

## What's in here

```
backend/     FastAPI app — routers → services → data access, SQLAlchemy +
             Alembic, chunking/retrieval/generation/guardrail services
frontend/    Vite + React — branded chat UI + admin view
corpus/      generate_corpus.py + 20 fictional Contoso Corp documents
             (5 markdown, 5 html, 5 docx, 5 pdf)
docs/        setup guide + design doc draft
```

## Quick start (see the setup guide for full detail)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in your Azure OpenAI / DeepSeek / Azure AI Search keys
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

Then open http://localhost:5173, upload the generated corpus documents on
the Knowledge base page, and start chatting.
