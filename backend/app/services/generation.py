"""
Generation provider abstraction.

GENERATION_PROVIDER in .env picks between:
- "azure_v1": the current-generation Azure OpenAI "v1" API
  (.../openai/v1/chat/completions), authenticated with a Bearer token,
  model named in the request body. This is what you're on if your
  project's sample code uses `OpenAI(base_url=".../openai/v1", api_key=...)`
  and `client.responses.create(model=deployment_name, ...)` — copy that
  base_url's host (everything before `/openai/v1`) into
  AZURE_OPENAI_ENDPOINT and this code builds the rest.
- "azure_openai": classic Azure OpenAI Service, one deployment = one URL
  path (.../openai/deployments/{name}/chat/completions), authenticated
  with an `api-key` header and an explicit `api-version` query param.
- "azure_foundry": the unified Azure AI Foundry Models inference endpoint
  (.../models/chat/completions), where the model you want is named in
  the request body instead of the URL, `api-key` header, explicit
  `api-version` query param.
- "deepseek": OpenAI-compatible API called directly (not through Azure),
  much cheaper per token — use this as the second option in your
  required cost/quality comparison if you have your own DeepSeek key.
- "claude": Anthropic API — highest quality instruction-following for the
  guardrail/refusal behavior in our testing; more expensive per token.

Every provider implements the same async generator signature so
routers/v1/chat.py can stream Server-Sent Events without caring which
provider is behind it.
"""
import json
from collections.abc import AsyncGenerator

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamProviderError
from app.services.guardrails import SYSTEM_PROMPT


def resolve_model_name(provider: str) -> str:
    """Display name for the model actually answering a given message —
    used for the per-message model label and the usage analytics
    breakdown. Kept in sync with which config value each provider branch
    below actually sends as `model`/deployment name."""
    settings = get_settings()
    if provider in ("azure_openai", "azure_foundry", "azure_v1"):
        return settings.azure_openai_chat_deployment
    if provider == "azure_deepseek":
        return settings.azure_deepseek_deployment
    if provider == "deepseek":
        return settings.deepseek_model
    if provider == "claude":
        return settings.claude_model
    return provider


async def stream_answer(user_turn: str, provider: str | None = None) -> AsyncGenerator[str, None]:
    settings = get_settings()
    provider = provider or settings.generation_provider

    if provider == "azure_openai":
        async for token in _stream_azure_openai_compatible(user_turn):
            yield token
    elif provider == "azure_foundry":
        async for token in _stream_azure_foundry(user_turn):
            yield token
    elif provider == "azure_v1":
        async for token in _stream_azure_v1(user_turn):
            yield token
    elif provider == "azure_deepseek":
        # Same Foundry endpoint/key as azure_v1, different deployment name.
        async for token in _stream_azure_v1(user_turn, model=settings.azure_deepseek_deployment):
            yield token
    elif provider == "deepseek":
        async for token in _stream_openai_compatible(
            user_turn,
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
        ):
            yield token
    elif provider == "claude":
        async for token in _stream_claude(user_turn):
            yield token
    else:
        raise UpstreamProviderError(f"Unknown generation provider: {provider}")


async def _stream_azure_openai_compatible(user_turn: str) -> AsyncGenerator[str, None]:
    settings = get_settings()
    url = (
        f"{settings.azure_openai_endpoint}/openai/deployments/"
        f"{settings.azure_openai_chat_deployment}/chat/completions"
        f"?api-version={settings.azure_openai_api_version}"
    )
    headers = {"api-key": settings.azure_openai_api_key, "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_turn},
        ],
        "stream": True,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise UpstreamProviderError(f"Azure OpenAI chat call failed: {resp.status_code} {body}")
            async for line in resp.aiter_lines():
                token = _parse_openai_sse_line(line)
                if token:
                    yield token


async def _stream_azure_v1(user_turn: str, model: str | None = None) -> AsyncGenerator[str, None]:
    """
    Azure OpenAI 'v1' API — confirmed against this project's own sample
    code (OpenAI Python SDK, base_url ending in /openai/v1, Bearer-token
    auth, model name in the request body, no api-version query param
    needed). Uses the standard OpenAI chat-completions wire format, which
    Azure's v1 API also supports for non-OpenAI models like DeepSeek.
    AZURE_OPENAI_ENDPOINT should be just the host, e.g.
    https://<your-resource>.services.ai.azure.com — this function
    appends /openai/v1/chat/completions itself.

    `model` lets a caller target a different deployment on this same
    endpoint/key (e.g. the "azure_deepseek" provider passes the DeepSeek
    deployment name here) — defaults to the configured chat deployment.
    """
    settings = get_settings()
    base = settings.azure_openai_endpoint.rstrip("/")
    if not base.endswith("/openai/v1"):
        base = f"{base}/openai/v1"
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.azure_openai_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model or settings.azure_openai_chat_deployment,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_turn},
        ],
        "stream": True,
        
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise UpstreamProviderError(f"Azure OpenAI v1 chat call failed: {resp.status_code} {body}")
            async for line in resp.aiter_lines():
                token = _parse_openai_sse_line(line)
                if token:
                    yield token


async def _stream_azure_foundry(user_turn: str) -> AsyncGenerator[str, None]:
    """
    Unified Azure AI Foundry Models inference endpoint. One endpoint
    ('.../models/chat/completions') serves every model deployed in the
    project — GPT, DeepSeek, whatever else — and you pick which one with
    the `model` field in the request body (the exact deployment name
    shown in your project's 'View deployments' table), not in the URL.
    This is what you're on if 'View deployments' lists GPT and DeepSeek
    together in one table with a shared 'Project endpoint'.
    """
    settings = get_settings()
    base = settings.azure_openai_endpoint.rstrip("/")
    url = f"{base}/models/chat/completions?api-version={settings.azure_foundry_api_version}"
    headers = {"api-key": settings.azure_openai_api_key, "Content-Type": "application/json"}
    payload = {
        "model": settings.azure_openai_chat_deployment,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_turn},
        ],
        "stream": True,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise UpstreamProviderError(f"Azure AI Foundry chat call failed: {resp.status_code} {body}")
            async for line in resp.aiter_lines():
                token = _parse_openai_sse_line(line)
                if token:
                    yield token


async def _stream_openai_compatible(user_turn: str, *, base_url: str, api_key: str, model: str) -> AsyncGenerator[str, None]:
    url = f"{base_url.rstrip('/')}/v1/chat/completions" if not base_url.endswith("/v1") else f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_turn},
        ],
        "stream": True,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise UpstreamProviderError(f"{model} chat call failed: {resp.status_code} {body}")
            async for line in resp.aiter_lines():
                token = _parse_openai_sse_line(line)
                if token:
                    yield token


def _parse_openai_sse_line(line: str) -> str | None:
    if not line or not line.startswith("data:"):
        return None
    data = line[len("data:"):].strip()
    if data == "[DONE]":
        return None
    try:
        obj = json.loads(data)
        choice = obj["choices"][0]
    except (json.JSONDecodeError, KeyError, IndexError):
        return None

    # A blocked response (Azure's content-safety layer, e.g. a jailbreak-
    # risk classifier) ends the stream with finish_reason=content_filter
    # and zero content deltas — surface this as a real error instead of
    # silently yielding nothing, which left the UI showing a blank message
    # bubble with no explanation.
    if choice.get("finish_reason") == "content_filter":
        detail = choice.get("content_filter_result", {}).get("error", {}).get("message")
        raise UpstreamProviderError(detail or "Response blocked by content filter.")

    return choice.get("delta", {}).get("content")


async def _stream_claude(user_turn: str) -> AsyncGenerator[str, None]:
    settings = get_settings()
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.claude_model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_turn}],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise UpstreamProviderError(f"Claude chat call failed: {resp.status_code} {body}")
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "content_block_delta":
                    text = obj.get("delta", {}).get("text")
                    if text:
                        yield text
