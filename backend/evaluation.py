from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from smolagents import InferenceClientModel


def _call_judge(
    *,
    model_id: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
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
            {"role": "system", "content": "You are a strict evaluation judge."},
            {"role": "user", "content": prompt},
        ]
    )
    content = response.content
    if isinstance(content, list):
        return "\n".join([str(item.get("text", "")) for item in content])
    return str(content or "")


@dataclass
class EvalResult:
    score: float
    metrics: dict[str, Any]
    judge_feedback: str | None = None


def _count_citations(text: str) -> int:
    return text.count("[")  # rough


def _has_sections(text: str) -> dict[str, bool]:
    sections = ["Overview", "Key Points", "Notable", "Sources", "概览", "要点", "数据", "来源"]
    found = {}
    lowered = text.lower()
    for s in sections:
        found[s] = s.lower() in lowered
    return found


def evaluate_report(
    *,
    topic: str,
    summary_md: str,
    sources: list[dict[str, Any]],
    min_sources: int,
    judge: dict[str, Any] | None = None,
) -> EvalResult:
    if not summary_md:
        return EvalResult(score=0.0, metrics={"error": "empty summary"})

    citations = _count_citations(summary_md)
    length = len(summary_md)
    section_flags = _has_sections(summary_md)
    section_score = sum(1 for v in section_flags.values() if v) / max(1, len(section_flags))

    source_count = len(sources or [])
    source_score = min(1.0, source_count / max(1, min_sources)) if min_sources else 1.0

    length_score = 1.0
    if length < 400:
        length_score = length / 400
    elif length > 2000:
        length_score = 2000 / length

    citation_score = min(1.0, citations / max(1, min_sources * 3))

    score = 0.25 * section_score + 0.25 * source_score + 0.25 * length_score + 0.25 * citation_score

    judge_feedback = None
    if judge:
        prompt = f"""
Evaluate the following report for topic: "{topic}".
Provide a JSON object with fields: score (0-10), strengths (list), weaknesses (list).

Report:\n{summary_md}
""".strip()
        judge_feedback = _call_judge(
            model_id=judge["model_id"],
            provider=judge.get("provider"),
            token=judge.get("token"),
            api_key=judge.get("api_key"),
            base_url=judge.get("base_url"),
            prompt=prompt,
        )

    metrics = {
        "length": length,
        "citations": citations,
        "source_count": source_count,
        "section_coverage": section_flags,
        "scores": {
            "sections": round(section_score, 3),
            "sources": round(source_score, 3),
            "length": round(length_score, 3),
            "citations": round(citation_score, 3),
        },
    }

    return EvalResult(score=round(score, 3), metrics=metrics, judge_feedback=judge_feedback)


def load_eval_dataset(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize_eval_scores(results: list[EvalResult]) -> dict[str, Any]:
    if not results:
        return {"count": 0, "avg_score": 0.0}
    scores = [r.score for r in results]
    return {
        "count": len(scores),
        "avg_score": round(sum(scores) / len(scores), 3),
        "min_score": round(min(scores), 3),
        "max_score": round(max(scores), 3),
        "std": round(math.sqrt(sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)), 3),
    }
