from __future__ import annotations

from typing import Any

from smolagents import InferenceClientModel


def _call_model(
    *,
    model_id: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
    system: str,
    prompt: str,
) -> str:
    model = InferenceClientModel(
        model_id=model_id,
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
    )
    response = model.generate(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    )
    content = response.content
    if isinstance(content, list):
        return "\n".join([str(item.get("text", "")) for item in content])
    return str(content or "")


def compress_source(
    *,
    topic: str,
    source: dict[str, Any],
    model_id: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
) -> str:
    snippets = source.get("snippets") or []
    snippet_block = "\n".join([f"- {s}" for s in snippets]) or "- (no snippets)"
    prompt = f"""
You are a research analyst. Extract 3-6 evidence bullets about "{topic}" using ONLY the snippets below.
Each bullet must be concise, factual, and end with the source id in [n] form.
If the snippet is insufficient, say so explicitly.

Source [{source['id']}]: {source['title']}
URL: {source['url']}
Snippets:\n{snippet_block}
""".strip()
    return _call_model(
        model_id=model_id,
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
        system="You extract evidence from sources without adding new facts.",
        prompt=prompt,
    )


def build_outline(
    *,
    topic: str,
    evidence: list[str],
    model_id: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
    lang: str,
) -> str:
    language = "Chinese (Simplified)" if lang.lower() in {"zh", "cn", "zh-cn", "chinese"} else "English"
    evidence_block = "\n".join([f"- {line}" for line in evidence])
    prompt = f"""
You are an outline planner. Build a concise report outline in {language} for topic: "{topic}".
Use only the evidence list. The outline should be 4-6 sections with 1-2 bullets each.

Evidence:\n{evidence_block}
""".strip()
    return _call_model(
        model_id=model_id,
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
        system="You create structured outlines for research reports.",
        prompt=prompt,
    )


def synthesize_report(
    *,
    topic: str,
    evidence: list[str],
    outline: str,
    model_id: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
    lang: str,
    min_sources: int,
) -> str:
    language = "Chinese (Simplified)" if lang.lower() in {"zh", "cn", "zh-cn", "chinese"} else "English"
    evidence_block = "\n".join([f"- {line}" for line in evidence])
    prompt = f"""
You are a research writer. Write a one-page report in {language} about "{topic}" using the outline and evidence.
Cite every key point with [n]. Do not add new facts beyond the evidence.
Use at least {min_sources} sources if possible.

Outline:\n{outline}\n\nEvidence:\n{evidence_block}

Output in Markdown:
- Title
- Overview (1 paragraph)
- Key Points (5-10 bullets, each with [n])
- Notable Data/Stats (bullets, or say \"No reliable stats found\")
- Sources (numbered list with title + URL)
""".strip()
    return _call_model(
        model_id=model_id,
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
        system="You write concise research summaries with citations.",
        prompt=prompt,
    )
