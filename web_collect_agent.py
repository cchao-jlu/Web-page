#!/usr/bin/env python3
import argparse
import os
import re
from datetime import datetime
from pathlib import Path

from smolagents import CodeAgent, InferenceClientModel, WebSearchTool, VisitWebpageTool
from smolagents.models import ChatMessage

from backend.openai_compat import chat_completion, extract_content
from backend.retrieval import enhanced_retrieve


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    if not text:
        text = f"topic-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return text


def resolve_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")


class OpenAICompatModel:
    supports_stop_parameter = True

    def __init__(self, *, model_id: str, api_key: str, base_url: str):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url

    def generate(self, messages, **kwargs):  # noqa: ANN001
        normalized = []
        for m in messages:
            if isinstance(m, dict):
                role = m.get("role")
                content = m.get("content")
            else:
                role = m.role
                content = m.content
            if role == "tool-call":
                role = "assistant"
                if content is None:
                    content = ""
            elif role == "tool-response":
                role = "tool"
                if content is None:
                    content = ""
            if content is None:
                content = ""
            if isinstance(content, list):
                content = "\n".join([str(item) for item in content])
            elif not isinstance(content, str):
                content = str(content)
            normalized.append({"role": role, "content": content})
        response = chat_completion(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model_id,
            messages=normalized,
        )
        content = extract_content(response)
        return ChatMessage(role="assistant", content=content, tool_calls=None, raw=response)


def build_model(model_id: str | None, provider: str | None, api_key: str | None, base_url: str | None):
    kwargs = {}
    token = resolve_token()
    if token:
        kwargs["token"] = token
    if model_id:
        kwargs["model_id"] = model_id
    if provider:
        kwargs["provider"] = provider
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        # Use OpenAI-compatible client if base_url is provided
        if not model_id:
            raise ValueError("model_id is required when using base_url (e.g., deepseek-chat).")
        if not api_key:
            raise ValueError("api_key is required when using base_url.")
        return OpenAICompatModel(model_id=model_id, api_key=api_key, base_url=base_url)
    return InferenceClientModel(**kwargs)


def build_task(topic: str, lang: str, min_sources: int) -> str:
    language = "Chinese (Simplified)" if lang.lower() in {"zh", "cn", "zh-cn", "chinese"} else "English"
    return f"""
You are a web research agent. Your goal is to collect and synthesize key information about the topic: "{topic}".

Steps:
1) Use web_search to find relevant and recent sources. Prefer diverse domains (news, official sites, reference docs).
2) Use visit_webpage to read the most relevant pages and extract key facts, data, and claims.
3) Produce a one-page summary in {language}. Keep it concise and well-structured.

Output requirements (Markdown only):
- Title
- Overview (1 short paragraph)
- Key Points (5-10 bullets)
- Notable Data/Stats (bullets, if available; otherwise say "No reliable stats found")
- Sources (numbered list with title + URL)

Quality rules:
- Cite every key point with a [n] reference that maps to the Sources list.
- Do not fabricate; if information is uncertain, say so explicitly.
- Use at least {min_sources} sources.
- Keep length roughly one page (around 400-700 Chinese characters or 300-600 English words).
""".strip()

def build_direct_prompt(topic: str, lang: str, min_sources: int, sources: list[dict]) -> str:
    language = "Chinese (Simplified)" if lang.lower() in {"zh", "cn", "zh-cn", "chinese"} else "English"
    sources_block = []
    for src in sources:
        snippets = "\n".join([f"- {s}" for s in src.get("snippets") or []]) or "- (no snippets)"
        sources_block.append(f"[{src['id']}] {src['title']}\nURL: {src['url']}\n{snippets}")
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


def make_min_sources_checker(min_sources: int):
    def _checker(final_answer: str, agent_memory=None, agent=None, **kwargs) -> bool:
        urls = re.findall(r"https?://\S+", final_answer)
        return len(urls) >= min_sources and "Sources" in final_answer

    return _checker


def run_agent(
    topic: str,
    *,
    model_id: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_results: int = 8,
    min_sources: int = 3,
    lang: str = "zh",
    output: str | None = None,
) -> tuple[str, str]:
    if base_url and api_key:
        if not model_id:
            model_id = "deepseek-chat"
        sources = enhanced_retrieve(topic, max_results=max_results, max_pages=min(max_results, 8))
        prompt = build_direct_prompt(topic, lang, min_sources, sources)
        model = build_model(model_id, provider, api_key, base_url)
        response = model.generate(
            messages=[
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        summary_md = response.content if isinstance(response.content, str) else str(response.content or "")
    else:
        model = build_model(model_id, provider, api_key, base_url)
        tools = [
            WebSearchTool(max_results=max_results),
            VisitWebpageTool(),
        ]

        agent = CodeAgent(
            tools=tools,
            model=model,
            final_answer_checks=[make_min_sources_checker(min_sources)],
        )

        task = build_task(topic, lang, min_sources)
        summary_md = agent.run(task)

    output_path = output
    if not output_path:
        slug = slugify(topic)
        output_path = str(Path("outputs") / f"{slug}.md")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(summary_md, encoding="utf-8")

    return summary_md, output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Web information collection agent (smolagents)")
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument("--model-id", default=os.getenv("SMOLAGENTS_MODEL_ID"), help="HF model id")
    parser.add_argument("--provider", default=os.getenv("SMOLAGENTS_PROVIDER"), help="Inference provider")
    parser.add_argument("--api-key", default=os.getenv("SMOLAGENTS_API_KEY"), help="API key for provider")
    parser.add_argument("--base-url", default=os.getenv("SMOLAGENTS_BASE_URL"), help="Base URL for provider")
    parser.add_argument("--max-results", type=int, default=8, help="Max search results")
    parser.add_argument("--min-sources", type=int, default=3, help="Minimum sources to cite")
    parser.add_argument("--lang", default=os.getenv("SMOLAGENTS_LANG", "zh"), help="Output language (zh or en)")
    parser.add_argument("--output", default=None, help="Output markdown file path")
    args = parser.parse_args()

    summary_md, output_path = run_agent(
        args.topic,
        model_id=args.model_id,
        provider=args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        max_results=args.max_results,
        min_sources=args.min_sources,
        lang=args.lang,
        output=args.output,
    )

    print(f"Saved summary to: {output_path}")
    print("\n---\n")
    print(summary_md)


if __name__ == "__main__":
    main()
