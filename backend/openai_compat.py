from __future__ import annotations

from typing import Any

import requests


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    timeout: int = 120,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if not response.ok:
        raise requests.HTTPError(
            f"{response.status_code} Client Error: {response.text} for url: {response.url}",
            response=response,
        )
    return response.json()


def extract_content(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except Exception:
        return ""
