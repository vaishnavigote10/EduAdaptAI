"""Optional LLM layer. Works with any OpenAI-compatible endpoint; returns None when not configured."""
import json, urllib.request
from django.conf import settings


def available():
    return bool(settings.LLM_API_KEY)


def chat(system, user, temperature=0.2):
    if not available():
        return None
    body = json.dumps({
        "model": settings.LLM_MODEL, "temperature": temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        settings.LLM_BASE_URL.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.LLM_API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
