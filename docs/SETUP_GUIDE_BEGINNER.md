# Setup Guide (Beginner Version) — DataFactZ RAG Knowledge Chatbot

You know Python. That's genuinely enough to get through this — everything
else below is explained from zero. Follow it in order, top to bottom,
don't skip ahead.

---

## Part 0 — Three ideas you need before anything makes sense

**"Resource group"** — think of it as a folder in Azure that holds all
the cloud "things" (services) for one project, so they can be managed and
billed together. You already have one called **`AI_Training`**. You won't
create a new one — everything you make in Azure goes inside this
existing folder.

**"Endpoint" and "API key"** — every Azure AI service you turn on gives
you two pieces of information: a **web address** (the endpoint — where
your code sends requests) and a **secret password** (the API key — proves
it's really you). Your Python code needs both, for every service. You'll
copy-paste each one into a file called `.env` later. Nobody else should
ever see these values.

**Two different Azure websites, two different jobs:**
- **portal.azure.com** — the general control panel for *everything*
  Azure. You'll use this once, to create one thing: Azure AI Search (the
  place your document chunks get stored so they can be searched).
- **ai.azure.com** (Microsoft Foundry) — the control panel specifically
  for AI models. You already have a project here called
  **`AI_Training_Project`**. You'll use this to turn on ("deploy") the
  two AI models this app needs: one that writes answers, one that turns
  text into numbers for search (embeddings).

That's the whole plan: **one thing in portal.azure.com, two model
deployments in ai.azure.com.** Let's do them one at a time.

---

## Part 1 — ai.azure.com: get your models' endpoint, key, and deployment names

Good news, based on what you described: **your manager already deployed
the models.** You don't need to deploy anything yourself — you just need
to collect four pieces of information.

1. Go to **https://ai.azure.com** and sign in.
2. Open the **`AI_Training_Project`** folder.
3. You're on the project's main page, where you can see:
   - A **"View deployments"** button
   - A **Key**
   - A **Project endpoint**
   - An **Azure OpenAI endpoint**

   Two different endpoints exist because this project can serve models
   two different ways. **Use the "Azure OpenAI endpoint" value** — that's
   the one this project's code is built for. (If that one doesn't work
   once you test it, come back and try the "Project endpoint" instead —
   see the note at the end of this section.)

4. Copy the **Key** and the **Azure OpenAI endpoint** somewhere safe —
   you'll paste both into `.env` in Part 3.

5. Click **"View deployments"**. You'll see a table with rows like
   `GPT-5`, `GPT-5.5`, `DeepSeek`, and a text-embedding model, each added
   by your manager.

6. **Pick which chat model you'll use** — `GPT-5.5` is a reasonable
   default if you're not sure. Click on that row. A panel opens showing
   its **Project endpoint**, **API key**, and a **sample code** snippet.

   **Copy the exact deployment name shown here** — the name in this
   table (e.g. it might literally be `gpt-5.5`, or something your
   manager renamed it to, like `chat-model-prod`) is what you must type
   into `.env`, not just "GPT-5.5" as a general label.

7. Click on the **text-embedding** row the same way, and copy its exact
   deployment name too.

8. **Write down these four things** for Part 3:
   - Azure OpenAI endpoint (from step 3/4)
   - API key (from step 3/4)
   - Chat model's exact deployment name (from step 6)
   - Embedding model's exact deployment name (from step 7)

**One thing to double check:** open the sample code shown for the chat
model in step 6, and look at the URL it calls. This project is set up
for the newer "unified" style, where the URL looks like
`.../models/chat/completions?api-version=...` and the model name is
inside the request body, not the URL. If the sample code you see instead
shows a URL shaped like `.../openai/deployments/<name>/chat/completions`
(the model name **inside the URL path**), that's the older "classic"
style — tell me exactly what the sample code shows and I'll flip one
setting in `.env` (`GENERATION_PROVIDER`/`EMBEDDINGS_PROVIDER`) to match
it; the rest of the app doesn't change either way.

---

## Part 2 — portal.azure.com: create Azure AI Search

1. Go to **https://portal.azure.com** and sign in.
2. In the search bar at the very top of the page, type **"Azure AI
   Search"** and click it in the results (not "Azure AI Search index" or
   anything else — just the plain service).
3. Click **"+ Create"**.
4. Fill in the form:
   - **Subscription:** leave whatever is already selected.
   - **Resource group:** click the dropdown and select **`AI_Training`**
     — the one already shared with you. Do not create a new one.
   - **Service name:** type something unique, like
     `contoso-search-<yourname>` (all lowercase, no spaces).
   - **Location:** leave the default, or pick the same region you saw
     used in `AI_Training_Project` if you noticed it.
   - **Pricing tier:** click "Change" if it's not already showing
     **Free** — select **Free**. (This is important: Free costs
     nothing; other tiers bill by the hour whether you use them or not.)
5. Click **"Review + create"**, then **"Create"**. Wait for the blue
   "Deployment succeeded" notification (roughly 1–2 minutes).
6. Click **"Go to resource"**.
7. In the left sidebar of this new resource, click **"Keys"**.
8. Copy the **URL** shown at the top of the Overview page (looks like
   `https://contoso-search-yourname.search.windows.net`) and the
   **Primary admin key** from the Keys page.
9. **Tag it** (small thing your program asked for): while still on this
   resource's page, look for **"Tags"** in the left sidebar → **"+ Add"**
   → Name: `owner`, Value: your name → **Apply**.

Now you have two more things saved:
   - Azure AI Search endpoint URL
   - Azure AI Search admin key

---

## Part 3 — Put everything into the project's `.env` file

Open the project folder in VS Code (`File > Open Folder`, pick the
`datafactz-rag` folder). In the file explorer on the left, open
`backend`, find the file called **`.env.example`**, and **duplicate it**
as **`.env`** (right-click → Copy, then Paste, then rename the copy to
exactly `.env`). This is the file your Python code actually reads —
`.env.example` is just a template.

Open `.env` and fill in the values you collected, replacing what's
already there:

```
VECTOR_BACKEND=azure
AZURE_SEARCH_ENDPOINT=<the Azure AI Search URL from Part 2>
AZURE_SEARCH_API_KEY=<the Azure AI Search admin key from Part 2>
AZURE_SEARCH_INDEX_NAME=contoso-kb

EMBEDDINGS_PROVIDER=azure_foundry
GENERATION_PROVIDER=azure_foundry
AZURE_OPENAI_ENDPOINT=<the "Azure OpenAI endpoint" from Part 1>
AZURE_OPENAI_API_KEY=<the Key from Part 1>
AZURE_OPENAI_CHAT_DEPLOYMENT=<the exact chat model deployment name from Part 1>
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=<the exact embedding model deployment name from Part 1>
```

`EMBEDDINGS_PROVIDER` and `GENERATION_PROVIDER` are both set to
`azure_foundry` because of the shared-deployments-table setup you
described in Part 1. If the sample code you checked turns out to show
the older per-deployment URL style instead, change both of these to
`azure_openai` instead — nothing else in this file needs to change.

Also set your own made-up password for the app itself (this is separate
from Azure — it's just how your own frontend proves to your own backend
that it's allowed to talk to it):

```
API_KEY=anything-you-make-up-like-my-secret-123
```

Leave every other line in `.env` exactly as it already is for now.

**Save the file.** That's it for Azure — everything from here is just
running commands in the VS Code terminal.

---

## Part 4 — Running the backend (the Python server)

Open a terminal inside VS Code: menu **Terminal → New Terminal**. You'll
type commands one line at a time, pressing Enter after each.

```bash
cd backend
```

This moves you into the `backend` folder. Now create an isolated Python
environment just for this project (so its packages don't mix with
anything else on your computer):

```bash
python -m venv .venv
```

Turn it on:

```bash
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

You'll know it worked because your terminal prompt now starts with
`(.venv)`. Every command from here runs inside that environment. Install
everything the backend needs:

```bash
pip install -r requirements.txt
```

This downloads all the Python libraries listed in `requirements.txt` —
it can take a minute or two the first time.

Create the local database file and its tables:

```bash
mkdir data
alembic upgrade head
```

`alembic` is the tool that builds your database's tables (`documents`,
`chunks`, `conversations`, `messages`, `citations`) based on the schema
already written in the code — you don't write any SQL yourself.

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running — this is your backend, alive and listening.
Open a browser and go to **http://localhost:8000/docs** — if you see a
page titled "DataFactZ RAG Chatbot" with a list of API endpoints, it
worked.

---

## Part 5 — Generate the sample documents

Open a **second** terminal tab in VS Code (don't close the first one —
the server needs to keep running). Click the **`+`** in the terminal
panel, or `Terminal → New Terminal` again.

```bash
cd corpus
python generate_corpus.py
```

This creates 20 fake "Contoso Corp" HR policy documents in
`corpus/markdown`, `corpus/html`, `corpus/docx`, and `corpus/pdf` — this
is the knowledge your chatbot will answer questions from.

---

## Part 6 — Running the frontend (the website you'll actually use)

Open a **third** terminal tab.

```bash
cd frontend
```

Check you have Node.js available (it lets you run JavaScript projects —
similar idea to how `python` runs Python projects):

```bash
node --version
```

If that shows a version number, you're fine. If it says "command not
found," you'll need nvm set up first (you mentioned you already have
this — run `nvm use --lts` if so).

Install the frontend's packages (same idea as `pip install`, just for
JavaScript):

```bash
npm install
```

Copy its settings file the same way you did for the backend:

```bash
cp .env.example .env
```

Open `frontend/.env` in VS Code and make sure `VITE_API_KEY` matches
**exactly** the `API_KEY` you made up in `backend/.env` back in Part 3.

Start it:

```bash
npm run dev
```

It will print a URL, almost always **http://localhost:5173**. Open that
in your browser.

---

## Part 7 — Try it out

1. In the browser, click **"Knowledge base"** in the left sidebar.
2. Click **"Upload document"** and pick one file at a time from the
   `corpus` folder you generated in Part 5 (start with just 2-3 files to
   confirm it works before uploading all 20).
3. Each upload should show up in the table within a few seconds, with a
   status of **"indexed"** and a chunk count.
4. Click **"Chat"** in the sidebar and ask a question about something in
   the document you uploaded — e.g. if you uploaded the PTO policy, ask
   *"How many PTO days do employees accrue per month?"*
5. You should see the answer stream in word by word, with a citation pill
   underneath showing which document it came from.

If step 4 gives you an error instead of an answer, see the
troubleshooting section at the bottom of `docs/SETUP_GUIDE.md` (the
original, more detailed version of this guide) — most first-time errors
are a mismatched `API_KEY`/`VITE_API_KEY`, or a typo in one of the Azure
values from Part 3.

---

## What to do next

Once this is working end to end:
- Upload all 20 generated documents.
- Test a question that's genuinely **not** in the corpus (e.g. "what's
  Contoso's stock ticker?") — it should say *"I don't have that in the
  knowledge base"* instead of guessing.
- Move on to filling in `docs/DESIGN_DOC.docx` with your own results.
