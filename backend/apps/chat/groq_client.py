"""
Minimal Groq client (OpenAI-compatible chat completions) using requests.

Groq's API speaks the OpenAI schema, including tool/function calling, so we post
messages (and optional tools) and read back either a text answer or tool_calls.
The API key lives in settings.GROQ_API_KEY (from .env), never in the frontend.
"""

import requests
from django.conf import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    pass


def is_configured():
    return bool(getattr(settings, "GROQ_API_KEY", ""))


def chat(messages, tools=None, tool_choice="auto", temperature=0.2, max_tokens=700):
    key = getattr(settings, "GROQ_API_KEY", "")
    if not key:
        raise GroqError("GROQ_API_KEY is not set.")
    model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=getattr(settings, "GROQ_TIMEOUT", 30),
        )
    except requests.RequestException as exc:
        raise GroqError(f"Could not reach Groq: {exc}")
    if r.status_code != 200:
        detail = ""
        try:
            detail = r.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            detail = r.text[:200]
        raise GroqError(f"Groq error {r.status_code}: {detail}")
    return r.json()["choices"][0]["message"]