# Azure Resource Setup — Contoso Knowledge Assistant

I can't create these resources for you directly — they live in your Azure
subscription and I have no access to your portal or credentials. This is
the exact click-path (and the CLI equivalent, if you'd rather run commands
in the VS Code terminal) to get everything this app needs, in order.

**Budget check first:** everything below fits on free/low tiers except
Azure AI Search's paid tiers, which bill hourly. Stick to the **Free**
search tier for a 20-document corpus and you should spend close to
nothing this week.

---

## 0. Prerequisites

- Access to the shared Resource Group your program gave you (or permission
  to create one).
- If you want to use the CLI instead of the Portal: [install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli),
  then in your VS Code terminal:
  ```bash
  az login
  az account set --subscription "<your subscription name or id>"
  ```

Set two variables you'll reuse in every command below (CLI path only):

```bash
RG="<your-shared-resource-group-name>"
LOCATION="eastus"        # or wherever your program's RG lives
YOURNAME="<your-name>"   # for the owner tag
```

---

## 1. Azure OpenAI (generation + embeddings)

### Portal path

1. Azure Portal → search **"Azure OpenAI"** → **Create**.
2. Select your shared Resource Group, a region that has OpenAI capacity
   (`East US`, `East US 2`, and `Sweden Central` are usually safe bets —
   availability varies by model), and a unique resource name.
3. Under **Tags**, add `owner` = your name (required by the brief's
   technical constraints).
4. Create. Once deployed, go to the resource → **"Go to Azure AI
   Foundry portal"** (this is where you deploy models — as of this
   writing Azure OpenAI resources are managed through Azure AI Foundry).
5. In Foundry, go to **Deployments → + Deploy model**:
   - Deploy a chat model: search for `gpt-4o-mini` (cheapest capable
     chat model as of this writing — confirm current pricing/availability
     since this changes). Name the deployment something you'll recognize,
     e.g. `gpt-4o-mini`.
   - Deploy an embeddings model: `text-embedding-3-small`. Name it e.g.
     `text-embedding-3-small`.
6. Back in the Azure Portal, on your Azure OpenAI resource →
   **"Keys and Endpoint"** → copy **KEY 1** and the **Endpoint**.
7. Put these into `backend/.env`:
   ```
   AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com
   AZURE_OPENAI_API_KEY=<KEY 1>
   AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
   AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-small
   AZURE_OPENAI_API_VERSION=2024-08-01-preview
   ```
   (Bump `AZURE_OPENAI_API_VERSION` if Azure has deprecated this version
   by the time you read this — the "Keys and Endpoint" page or the
   Foundry deployment details page shows the current supported versions.)

### CLI path (resource creation only — model deployment currently needs the Foundry portal UI)

```bash
az cognitiveservices account create \
  --name "contoso-aoai-$YOURNAME" \
  --resource-group "$RG" \
  --kind OpenAI \
  --sku S0 \
  --location "$LOCATION" \
  --tags owner="$YOURNAME"

az cognitiveservices account keys list \
  --name "contoso-aoai-$YOURNAME" \
  --resource-group "$RG"
```

Then go deploy the two models via the Foundry portal link as in step 4-5
above — CLI-based deployment (`az cognitiveservices account deployment
create`) works too if you prefer scripting it end to end:

```bash
az cognitiveservices account deployment create \
  --name "contoso-aoai-$YOURNAME" --resource-group "$RG" \
  --deployment-name "gpt-4o-mini" \
  --model-name "gpt-4o-mini" --model-version "2024-07-18" \
  --model-format OpenAI --sku-capacity 10 --sku-name "Standard"

az cognitiveservices account deployment create \
  --name "contoso-aoai-$YOURNAME" --resource-group "$RG" \
  --deployment-name "text-embedding-3-small" \
  --model-name "text-embedding-3-small" --model-version "1" \
  --model-format OpenAI --sku-capacity 10 --sku-name "Standard"
```

---

## 2. Azure AI Search (the vector store)

### Portal path

1. Azure Portal → search **"Azure AI Search"** → **Create**.
2. Same Resource Group, **Free** pricing tier (fine for 20 documents —
   50MB storage cap, 3 indexes max).
3. Tag `owner` = your name.
4. Create. Once deployed, go to **"Keys"** → copy the **Primary admin key**
   and the URL shown at the top of the Overview page.
5. Put these into `backend/.env`:
   ```
   VECTOR_BACKEND=azure
   AZURE_SEARCH_ENDPOINT=https://<your-service-name>.search.windows.net
   AZURE_SEARCH_API_KEY=<primary admin key>
   AZURE_SEARCH_INDEX_NAME=contoso-kb
   ```
   You don't need to create the index yourself — the backend does it
   automatically on first ingestion (`AzureSearchVectorStore._ensure_index`
   in `app/services/vector_store.py`).

### CLI path

```bash
az search service create \
  --name "contoso-search-$YOURNAME" \
  --resource-group "$RG" \
  --sku free \
  --location "$LOCATION" \
  --tags owner="$YOURNAME"

az search admin-key show \
  --service-name "contoso-search-$YOURNAME" \
  --resource-group "$RG"
```

**Free tier limits to know about:** 3 indexes, 50MB storage, no semantic
ranker. All fine for this assignment. If you outgrow it (bigger corpus,
need semantic re-ranking for the stretch goal), the next step up is
Basic — which does bill hourly, so only upgrade when you're actively
using it and remember to delete it afterward.

---

## 3. (Optional) DeepSeek — for your required generation comparison

This isn't an Azure resource — get an API key directly from DeepSeek's
platform (platform.deepseek.com), then:

```
DEEPSEEK_API_KEY=<your key>
```

Flip `GENERATION_PROVIDER=deepseek` in `.env`, re-run your test questions,
and record latency/quality/cost differences in the design doc's Section
7.4 — that satisfies "compare at least two options for generation."

---

## 4. Verify everything is wired correctly

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Then, in a separate terminal:

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: <your API_KEY>" \
  -F "file=@../corpus/markdown/paid_time_off_policy.md"
```

A successful response looks like:
```json
{"document": {"id": "...", "status": "indexed", "chunk_count": 4, ...}, "chunks_created": 4}
```

If this fails, check in order: (1) `AZURE_OPENAI_*` values are correct and
the deployment names match exactly what you named them in Foundry, (2) if
`VECTOR_BACKEND=azure`, that the search service is fully provisioned
(can take a minute after creation) and the key is the **admin** key, not
a query key.

---

## 5. Cost hygiene checklist (do this before you close your laptop each day)

- [ ] Azure AI Search: Free tier costs nothing idle — no action needed.
      If you upgraded to Basic/Standard for testing semantic ranking,
      **delete it** when done: `az search service delete --name ... --resource-group "$RG"`.
- [ ] Azure OpenAI: billed per token, not per hour — safe to leave
      provisioned, but don't leave a load-test script running against it.
- [ ] Confirm every resource you created has the `owner=<yourname>` tag
      (technical constraint in the brief) — you can check all of them at
      once with:
      ```bash
      az resource list --resource-group "$RG" --query "[].{name:name, tags:tags}" -o table
      ```
