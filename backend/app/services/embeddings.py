"""
Embeddings provider abstraction.

Section 3 asks you to "compare at least two options for generation or
embeddings and record quality/cost observations" — do that comparison for
embeddings here, since it is the cheaper of the two to A/B (see
docs/DESIGN_DOC.md section on model choice). Swap EMBEDDINGS_PROVIDER in
.env between "azure_openai" and "deepseek" to run the same corpus through
both and compare retrieval quality on your 5-10 test questions.
"""
import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamProviderError


async def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if settings.embeddings_provider == "azure_openai":
        return await _embed_azure_openai(texts)
    elif settings.embeddings_provider == "azure_foundry":
        return await _embed_azure_foundry(texts)
    elif settings.embeddings_provider == "azure_v1":
        return await _embed_azure_v1(texts)
    elif settings.embeddings_provider == "deepseek":
        return await _embed_deepseek(texts)
    else:
        raise UpstreamProviderError(f"Unknown embeddings provider: {settings.embeddings_provider}")


async def _embed_azure_v1(texts: list[str]) -> list[list[float]]:
    """
    Matching pair to generation.py::_stream_azure_v1 — same /openai/v1
    host, same Bearer-token auth, model name in the body.
    """
    settings = get_settings()
    base = settings.azure_openai_endpoint.rstrip("/")
    if not base.endswith("/openai/v1"):
        base = f"{base}/openai/v1"
    url = f"{base}/embeddings"
    headers = {"Authorization": f"Bearer {settings.azure_openai_api_key}", "Content-Type": "application/json"}
    payload = {"model": settings.azure_openai_embeddings_deployment, "input": texts}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise UpstreamProviderError(f"Azure OpenAI v1 embeddings call failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


async def _embed_azure_foundry(texts: list[str]) -> list[list[float]]:
    """
    Unified Azure AI Foundry Models inference endpoint — the one you get
    when your project's 'Deployments' table lists GPT and DeepSeek models
    side by side. One endpoint serves every model; the model you want is
    named in the request body (`model`), not in the URL path like classic
    Azure OpenAI. Confirmed against the sample code shown when you click a
    deployment in ai.azure.com > your project > View deployments.
    """
    settings = get_settings()
    base = settings.azure_openai_endpoint.rstrip("/")
    url = f"{base}/models/embeddings?api-version={settings.azure_foundry_api_version}"
    headers = {"api-key": settings.azure_openai_api_key, "Content-Type": "application/json"}
    payload = {"model": settings.azure_openai_embeddings_deployment, "input": texts}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise UpstreamProviderError(f"Azure AI Foundry embeddings call failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


async def _embed_azure_openai(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    url = (
        f"{settings.azure_openai_endpoint}/openai/deployments/"
        f"{settings.azure_openai_embeddings_deployment}/embeddings"
        f"?api-version={settings.azure_openai_api_version}"
    )
    headers = {"api-key": settings.azure_openai_api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json={"input": texts})
    if resp.status_code != 200:
        raise UpstreamProviderError(f"Azure OpenAI embeddings call failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


async def _embed_deepseek(texts: list[str]) -> list[list[float]]:
    # NOTE: as of this writing DeepSeek's public API does not expose a
    # dedicated embeddings endpoint. This stub is here so the provider
    # switch in .env is real and documented; if/when they ship one, point
    # this at it. Until then, leave EMBEDDINGS_PROVIDER=azure_openai and
    # only use DeepSeek for GENERATION_PROVIDER (see generation.py) — note
    # this limitation explicitly in your design doc's comparison table.
    raise UpstreamProviderError(
        "DeepSeek does not currently offer a public embeddings endpoint. "
        "Use EMBEDDINGS_PROVIDER=azure_openai."
    )
