import re
from urllib.parse import urlparse

from smolagents import VisitWebpageTool, WebSearchTool


def parse_search_results(markdown: str) -> list[dict]:
    blocks = [b.strip() for b in markdown.split("\n\n") if b.strip()]
    results = []
    for block in blocks:
        match = re.search(r"\[(.*?)\]\((https?://[^)]+)\)", block)
        if not match:
            continue
        title = match.group(1).strip()
        url = match.group(2).strip()
        desc_lines = [line.strip() for line in block.splitlines()[1:] if line.strip()]
        description = " ".join(desc_lines)
        results.append({"title": title, "url": url, "description": description})
    return results


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def filter_results(
    results: list[dict],
    *,
    allow_domains: list[str] | None = None,
    block_domains: list[str] | None = None,
    max_results: int = 10,
) -> list[dict]:
    allow = [d.lower() for d in allow_domains or []]
    block = [d.lower() for d in block_domains or []]
    seen = set()
    filtered = []
    for item in results:
        domain = normalize_domain(item["url"])
        if allow and not any(domain.endswith(d) for d in allow):
            continue
        if block and any(domain.endswith(d) for d in block):
            continue
        key = (domain, item["url"])
        if key in seen:
            continue
        seen.add(key)
        filtered.append(item)
        if len(filtered) >= max_results:
            break
    return filtered


def extract_snippets(text: str, max_snippets: int = 6) -> list[str]:
    if not text:
        return []
    lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]
    candidates = []
    keywords = [
        "policy",
        "regulation",
        "发布",
        "研究",
        "报告",
        "市场",
        "增长",
        "标准",
        "风险",
        "应用",
    ]
    for line in lines:
        if len(line) < 40:
            continue
        if re.search(r"\d", line) or any(k in line.lower() for k in keywords):
            candidates.append(line)
    if not candidates:
        candidates = lines[:max_snippets]
    snippets = []
    seen = set()
    for line in candidates:
        if line in seen:
            continue
        seen.add(line)
        snippets.append(line)
        if len(snippets) >= max_snippets:
            break
    return snippets


def enhanced_retrieve(
    topic: str,
    *,
    max_results: int = 8,
    max_pages: int = 5,
    allow_domains: list[str] | None = None,
    block_domains: list[str] | None = None,
) -> list[dict]:
    search_tool = WebSearchTool(max_results=max_results)
    visit_tool = VisitWebpageTool()
    search_md = search_tool.forward(topic)
    results = parse_search_results(search_md)
    results = filter_results(
        results,
        allow_domains=allow_domains,
        block_domains=block_domains,
        max_results=max_pages,
    )

    sources = []
    for idx, item in enumerate(results, start=1):
        content = visit_tool.forward(item["url"])
        snippets = extract_snippets(content)
        sources.append(
            {
                "id": idx,
                "title": item["title"],
                "url": item["url"],
                "description": item["description"],
                "snippets": snippets,
            }
        )
    return sources
