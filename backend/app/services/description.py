import base64
import json
import logging
from typing import Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

VALID_PROVIDERS = {"anthropic", "openai"}


def encode_image_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def build_prompt(names: list[str], boxes: list[list[int]]) -> str:
    names_str = ", ".join(names) if names else "unknown people"
    return (
        f"You are given an image with the following recognized people: {names_str}. "
        f"Each person has a bounding box shown in the image. "
        f"For EACH recognized person (not unknowns), describe what they are doing in 1 to 4 words "
        f"(e.g. 'smiling', 'talking', 'wearing glasses', 'looking at camera'). "
        f"Return ONLY valid JSON in this exact format: "
        f'{{"people":[{{"name":"<name>","doing":"<1-4 word description>"}}]}} '
        f"If you cannot determine what a person is doing, use 'posing'. "
        f"Do NOT include unknown people. Do NOT explain. Return ONLY the JSON."
    )


async def call_anthropic(
    image_b64s: list[str],
    prompt: str,
    model: str,
) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        content = []
        for img_b64 in image_b64s:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64,
                },
            })
        content.append({"type": "text", "text": prompt})

        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.AI_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": content}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text_content = data["content"][0]["text"]
        return _parse_json_response(text_content)


async def call_openai(
    image_b64s: list[str],
    prompt: str,
    model: str,
) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
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

        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": content}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text_content = data["choices"][0]["message"]["content"]
        return _parse_json_response(text_content)


def _parse_json_response(text: str) -> Optional[dict]:
    text = text.strip()
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


async def describe_people(
    image_bytes_list: list[bytes],
    names: list[str],
    boxes: list[list[int]],
) -> dict[str, str]:
    """Call vision LLM to describe what each recognized person is doing.
    Returns dict mapping name -> doing description.
    Falls back gracefully on error.
    """
    if not settings.AI_API_KEY or settings.AI_API_KEY == "your-api-key-here":
        logger.warning("No AI API key configured, skipping description")
        return {}

    image_b64s = [encode_image_b64(img) for img in image_bytes_list]
    prompt = build_prompt(names, boxes)

    provider = settings.AI_PROVIDER.lower()
    model = settings.AI_MODEL

    try:
        if provider == "anthropic":
            result = await call_anthropic(image_b64s, prompt, model)
        elif provider == "openai":
            result = await call_openai(image_b64s, prompt, model)
        else:
            logger.error("Unknown AI provider: %s", provider)
            return {}
    except httpx.HTTPStatusError as e:
        logger.error("LLM API HTTP error: %s %s", e.response.status_code, e.response.text[:200])
        return {}
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {}

    if not result or "people" not in result:
        return {}

    descriptions = {}
    for person in result["people"]:
        name = person.get("name", "").strip()
        doing = person.get("doing", "").strip()
        if name and doing:
            descriptions[name] = doing

    return descriptions
