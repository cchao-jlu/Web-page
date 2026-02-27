#!/usr/bin/env python3
import argparse
import os
import re
from datetime import datetime
from pathlib import Path

from smolagents import CodeAgent, InferenceClientModel, WebSearchTool, VisitWebpageTool


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    if not text:
        text = f"topic-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return text


def resolve_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")


def build_model(model_id: str | None, provider: str | None):
    kwargs = {}
    token = resolve_token()
    if token:
        kwargs["token"] = token
    if model_id:
        kwargs["model_id"] = model_id
    if provider:
        kwargs["provider"] = provider
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


def make_min_sources_checker(min_sources: int):
    def _checker(final_answer: str, agent_memory=None) -> bool:
        urls = re.findall(r"https?://\S+", final_answer)
        return len(urls) >= min_sources and "Sources" in final_answer

    return _checker


def run_agent(
    topic: str,
    *,
    model_id: str | None = None,
    provider: str | None = None,
    max_results: int = 8,
    min_sources: int = 3,
    lang: str = "zh",
    output: str | None = None,
) -> tuple[str, str]:
    model = build_model(model_id, provider)
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
    parser.add_argument("--max-results", type=int, default=8, help="Max search results")
    parser.add_argument("--min-sources", type=int, default=3, help="Minimum sources to cite")
    parser.add_argument("--lang", default=os.getenv("SMOLAGENTS_LANG", "zh"), help="Output language (zh or en)")
    parser.add_argument("--output", default=None, help="Output markdown file path")
    args = parser.parse_args()

    summary_md, output_path = run_agent(
        args.topic,
        model_id=args.model_id,
        provider=args.provider,
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
