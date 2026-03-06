from __future__ import annotations

from typing import Any

from smolagents import InferenceClientModel


def build_prompt(topic: str, lang: str, sources: list[dict[str, Any]], min_sources: int) -> str:
    language = "Chinese (Simplified)" if lang.lower() in {"zh", "cn", "zh-cn", "chinese"} else "English"
    sources_block = []
    for src in sources:
        snippets = "\n".join([f"- {s}" for s in src.get("snippets") or []])
        sources_block.append(
            f"[{src['id']}] {src['title']}\nURL: {src['url']}\n" + (snippets if snippets else "- (no snippets)")
        )
    joined_sources = "\n\n".join(sources_block)

    return f"""
You are a research summarizer. Write a one-page summary in {language} about: "{topic}".

Use ONLY the provided sources below. Cite key points with [n] where n matches the source id.
If a claim is uncertain, say so explicitly. Use at least {min_sources} sources if possible.

Output in Markdown with:
- Title
- Overview (1 short paragraph)
- Key Points (5-10 bullets, each with [n])
- Notable Data/Stats (bullets, or say "No reliable stats found")
- Sources (numbered list with title + URL)

Sources:
{joined_sources}
""".strip()


def generate_summary(
    *,
    topic: str,
    lang: str,
    sources: list[dict[str, Any]],
    min_sources: int,
    model_id: str | None,
    provider: str | None,
    token: str | None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    model = InferenceClientModel(
        model_id=model_id or "Qwen/Qwen3-Next-80B-A3B-Thinking",
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
    )
    prompt = build_prompt(topic, lang, sources, min_sources)
    response = model.generate(
        messages=[
            {"role": "system", "content": "You are a helpful research assistant."},
            {"role": "user", "content": prompt},
        ]
    )
    content = response.content
    if isinstance(content, list):
        return "\n".join([str(item.get("text", "")) for item in content])
    return str(content or "")
