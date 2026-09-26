import asyncio
import base64
import json
import logging
import random
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

VALID_PROVIDERS = {"gemini", "groq", "openai"}

GEMINI_GENERATE_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

_KNOWN_PLACEHOLDERS = {
    "your-api-key-here",
    "your-gemini-api-key-here",
    "your-groq-api-key-here",
    "your-new-anthropic-key-here",
}


def encode_image_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def build_prompt(names: list[str], boxes: list[list[int]]) -> str:
    names_str = ", ".join(names) if names else "unknown people"
    return (
        f"You are given an image with the following recognized people: {names_str}. "
        f"For EACH recognized person (not unknowns), write a sarcastic but playful "
        f"2-sentence message describing what they appear to be doing "
        f"(e.g. \"Oh sure, just smiling at the camera like you're the most "
        f"interesting person here. Real original, genius.\"). "
        f"Keep it teasing, never mean. "
        f"Return ONLY valid JSON in this exact format: "
        f'{{"people":[{{"name":"<name>","doing":"<sarcastic 2-sentence message>"}}]}} '
        f"If you cannot determine anything, use a generic sarcastic remark. "
        f"Do NOT include unknown people. Do NOT explain. Return ONLY the JSON."
    )


def build_video_prompt(name: str, num_frames: int) -> str:
    return (
        f"You are given {num_frames} frames sampled from a video showing the "
        f"recognized person '{name}'. "
        f"The frames are in chronological order. "
        f"Write a sarcastic but playful 2-sentence message capturing what this person "
        f"is doing across the clip "
        f"(e.g. \"Wow, look at them strolling toward the door like they invented "
        f"walking. Better watch out, door.\"). "
        f"Keep it teasing, never mean. "
        f"Return ONLY valid JSON in this exact format: "
        f'{{"people":[{{"name":"<name>","doing":"<sarcastic 2-sentence message>"}}]}} '
        f"If you cannot determine an activity, use a generic sarcastic remark. "
        f"Do NOT explain. Return ONLY the JSON."
    )


async def call_gemini_generate_content(
    image_b64s: list[str],
    prompt: str,
    model: str,
    api_key: str,
    retries: int = 0,
) -> Optional[dict]:
    """Call Gemini's native generateContent endpoint.

    Model goes in the URL path; auth uses `x-goog-api-key`; images are sent as
    `inline_data` parts (multiple images = multiple parts). Text is read from
    `candidates[0].content.parts[0].text`.
    """
    parts: list[dict] = [
        {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
        for b64 in image_b64s
    ]
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts, "role": "user"}],
        "generationConfig": {"maxOutputTokens": 400},
    }

    async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
        for attempt in range(retries + 1):
            try:
                response = await client.post(
                    GEMINI_GENERATE_ENDPOINT.format(model=model),
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return None
                parts_out = (
                    candidates[0].get("content", {}).get("parts") or []
                )
                text = parts_out[0]["text"] if parts_out else ""
                return _parse_json_response(text)
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in RETRYABLE_STATUSES and attempt < retries:
                    delay = min(2.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.3)
                    logger.warning(
                        "Model %s HTTP %s (attempt %d/%d), retrying in %.1fs",
                        model, status, attempt + 1, retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise


async def call_chat_completions(
    endpoint: str,
    api_key: str,
    image_b64s: list[str],
    prompt: str,
    model: str,
    retries: int = 0,
) -> Optional[dict]:
    """Call an OpenAI-compatible chat completions endpoint (Groq, OpenAI).

    Auth is `Authorization: Bearer <api_key>` and the response is read
    from `choices[0].message.content`. Multiple images may be passed in a
    single request as base64 data URLs.
    Transient failures (429/5xx) are retried with exponential backoff.
    """
    content = []
    for img_b64 in image_b64s:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}",
                "detail": "low",
            },
        })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": model,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": content}],
    }

    async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
        for attempt in range(retries + 1):
            try:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text_content = data["choices"][0]["message"]["content"]
                return _parse_json_response(text_content)
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in RETRYABLE_STATUSES and attempt < retries:
                    delay = min(2.0, 0.5 * (2 ** attempt)) + random.uniform(0, 0.3)
                    logger.warning(
                        "Model %s HTTP %s (attempt %d/%d), retrying in %.1fs",
                        model, status, attempt + 1, retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise


def _parse_json_response(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        return None


def _provider_credentials(provider: str):
    """Returns (api_key, key_name) for the configured provider."""
    if provider == "gemini":
        return settings.GEMINI_API_KEY, "GEMINI_API_KEY"
    if provider == "groq":
        return settings.GROQ_API_KEY, "GROQ_API_KEY"
    if provider == "openai":
        return settings.OPENAI_API_KEY, "OPENAI_API_KEY"
    return None, None


async def describe_people(
    image_bytes_list: list[bytes],
    names: list[str],
    boxes: list[list[int]],
    warning_out: Optional[list[str]] = None,
    video: bool = False,
) -> dict[str, str]:
    """Call the vision LLM to describe what each recognized person is doing.
    For photos, sends the single image. For video, `image_bytes_list` should be
    frames sampled across the clip and `video=True` switches to the
    activity-over-time prompt; all frames go into one request as multiple
    image parts.
    Returns dict mapping name -> doing message.
    On error, appends a human-readable reason to `warning_out` (if given)
    and returns {} so recognition results are never lost.
    """
    def _warn(msg: str):
        logger.warning(msg)
        if warning_out is not None:
            warning_out.append(msg)

    provider = settings.AI_PROVIDER.lower()
    model = settings.AI_MODEL

    key, key_name = _provider_credentials(provider)
    if key is None:
        _warn(f"AI descriptions unavailable: unknown AI_PROVIDER '{provider}'")
        return {}

    if not key or key.strip().lower() in _KNOWN_PLACEHOLDERS:
        _warn(f"AI descriptions disabled: {key_name} not set in .env")
        return {}
    if provider == "groq" and not key.startswith("gsk_"):
        _warn(
            "AI descriptions disabled: GROQ_API_KEY does not look like a Groq key "
            "(it should start with 'gsk_'). Did you paste a different provider's key?"
        )
        return {}
    if provider == "gemini" and key.startswith("sk-ant"):
        _warn(
            "AI descriptions disabled: GEMINI_API_KEY looks like an Anthropic key "
            "(starts with 'sk-ant'). Paste a Google Gemini API key instead."
        )
        return {}

    if not model:
        _warn(
            "AI descriptions disabled: AI_MODEL is empty in .env "
            "(set it to a vision-capable model such as 'gemini-flash-latest')."
        )
        return {}

    image_b64s = [encode_image_b64(img) for img in image_bytes_list]
    prompt = (
        build_video_prompt(names[0] if names else "the person", len(image_b64s))
        if video
        else build_prompt(names, boxes)
    )

    try:
        if provider == "gemini":
            try:
                result = await call_gemini_generate_content(
                    image_b64s, prompt, model, key,
                    retries=settings.AI_MAX_RETRIES,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in RETRYABLE_STATUSES:
                    raise
                fallback = settings.AI_FALLBACK_MODEL
                if not fallback or fallback == model:
                    raise
                logger.warning(
                    "Model %s unavailable (HTTP %s); trying fallback model %s",
                    model, e.response.status_code, fallback,
                )
                result = await call_gemini_generate_content(
                    image_b64s, prompt, fallback, key,
                    retries=settings.AI_MAX_RETRIES,
                )
        elif provider == "groq":
            result = await call_chat_completions(
                GROQ_ENDPOINT, key, image_b64s, prompt, model,
                retries=settings.AI_MAX_RETRIES,
            )
        else:
            result = await call_chat_completions(
                OPENAI_ENDPOINT, key, image_b64s, prompt, model,
                retries=settings.AI_MAX_RETRIES,
            )
    except httpx.HTTPStatusError as e:
        _warn(
            f"AI description API failed ({provider}/{model}): "
            f"HTTP {e.response.status_code} — {e.response.text[:200]}"
        )
        return {}
    except Exception as e:
        _warn(f"AI description call failed ({provider}/{model}): {e}")
        return {}

    if not result or "people" not in result:
        if result is None:
            logger.warning("Vision model returned no parseable JSON for %s/%s", provider, model)
        return {}

    entries = result.get("people") or []
    descriptions = {}
    for person in entries:
        name = person.get("name", "").strip()
        doing = person.get("doing", "").strip()
        if name and doing:
            descriptions[name] = doing

    # Name-mismatch fallback: if the model wrote a different name for one of our
    # recognized people, map the result to `names` by position (same order).
    for i, n in enumerate(names):
        if n not in descriptions and i < len(entries):
            doing = entries[i].get("doing", "").strip()
            if doing:
                descriptions[n] = doing

    return descriptions