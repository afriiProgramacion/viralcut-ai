import json, httpx
from ..config import settings


def _anthropic_key(db_val: str | None = None) -> str:
    return (db_val or settings.anthropic_api_key or "").strip()


def _openai_key(db_val: str | None = None) -> str:
    return (db_val or settings.openai_api_key or "").strip()


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
}


def resolve_provider(cfg: dict) -> tuple[str, str, str]:
    """Return (provider, model, api_key)."""
    provider = (cfg.get("ai_provider") or settings.ai_provider or "anthropic").strip()
    model = (cfg.get("ai_model") or settings.ai_model or "").strip()
    if not model:
        model = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["anthropic"])
    if provider == "anthropic":
        key = _anthropic_key(cfg.get("anthropic_api_key"))
    elif provider == "openai":
        key = _openai_key(cfg.get("openai_api_key"))
    else:
        key = ""
    return provider, model, key


async def chat(cfg: dict, system: str, user: str, max_tokens: int = 4000) -> str:
    provider, model, key = resolve_provider(cfg)
    if provider == "local" or not key:
        raise RuntimeError("No AI API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env or settings.")
    if provider == "anthropic":
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
        if r.status_code != 200:
            raise RuntimeError(f"Anthropic error {r.status_code}: {r.text[:500]}")
        data = r.json()
        return data["content"][0]["text"]
    else:
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.4,
                },
            )
        if r.status_code != 200:
            raise RuntimeError(f"OpenAI error {r.status_code}: {r.text[:500]}")
        data = r.json()
        return data["choices"][0]["message"]["content"]


def parse_json(text: str):
    text = text.strip()
    # strip code fences
    if text.startswith("```"):
        # remove first fence
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # find first { or [
    import re
    m = re.search(r"[\{\[]", text)
    if m:
        start = m.start()
        # try to parse from start
        candidate = text[start:]
        # attempt trailing trim: find matching end
        try:
            return json.loads(candidate)
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from model output: {e}\n---\n{text[:500]}")
