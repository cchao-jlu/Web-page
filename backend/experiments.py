from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import db  # noqa: E402
from backend.app import ReportRequest  # noqa: E402
from backend.evaluation import EvalResult, evaluate_report, summarize_eval_scores  # noqa: E402
from backend.pipeline import build_outline, compress_source, synthesize_report  # noqa: E402
from backend.retrieval import enhanced_retrieve  # noqa: E402

RESULTS_DIR = Path("results")


def run_single_experiment(
    *,
    topic: str,
    lang: str,
    min_sources: int,
    max_results: int,
    max_pages: int,
    provider: str | None,
    model_id: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
) -> dict[str, Any]:
    payload = ReportRequest(
        topic=topic,
        lang=lang,
        min_sources=min_sources,
        max_results=max_results,
        max_pages=max_pages,
        model_id=model_id or ("deepseek-chat" if base_url else None),
        provider=provider,
        token=token,
        api_key=api_key,
        base_url=base_url,
    )

    sources = enhanced_retrieve(
        payload.topic,
        max_results=payload.max_results,
        max_pages=payload.max_pages,
        allow_domains=payload.allow_domains,
        block_domains=payload.block_domains,
    )

    evidence_outputs = []
    for src in sources:
        evidence = compress_source(
            topic=payload.topic,
            source=src,
            model_id=payload.model_id or "deepseek-chat",
            provider=payload.provider,
            token=payload.token,
            api_key=payload.api_key,
            base_url=payload.base_url,
        )
        src["evidence"] = evidence
        evidence_outputs.append(evidence)

    outline = build_outline(
        topic=payload.topic,
        evidence=evidence_outputs,
        model_id=payload.model_id or "deepseek-chat",
        provider=payload.provider,
        token=payload.token,
        api_key=payload.api_key,
        base_url=payload.base_url,
        lang=payload.lang,
    )

    summary = synthesize_report(
        topic=payload.topic,
        evidence=evidence_outputs,
        outline=outline,
        model_id=payload.model_id or "deepseek-chat",
        provider=payload.provider,
        token=payload.token,
        api_key=payload.api_key,
        base_url=payload.base_url,
        lang=payload.lang,
        min_sources=payload.min_sources,
    )

    eval_result: EvalResult = evaluate_report(
        topic=payload.topic,
        summary_md=summary,
        sources=sources,
        min_sources=payload.min_sources,
        judge=None,
    )

    return {
        "topic": payload.topic,
        "lang": payload.lang,
        "min_sources": payload.min_sources,
        "max_results": payload.max_results,
        "max_pages": payload.max_pages,
        "provider": payload.provider,
        "model_id": payload.model_id,
        "score": eval_result.score,
        "metrics": eval_result.metrics,
        "summary_md": summary,
        "sources": sources,
    }


def run_experiments(
    *,
    dataset_path: str,
    config_path: str,
    provider: str | None,
    token: str | None,
    api_key: str | None,
    base_url: str | None,
) -> dict[str, Any]:
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    runs = config.get("runs", [])

    results = []
    for run in runs:
        run_model_id = None if base_url else run.get("model_id")
        for item in dataset:
            result = run_single_experiment(
                topic=item["topic"],
                lang=item.get("lang", "zh"),
                min_sources=item.get("min_sources", 3),
                max_results=run.get("max_results", 8),
                max_pages=run.get("max_pages", 5),
                provider=run.get("provider") or provider,
                model_id=run_model_id,
                token=token,
                api_key=api_key,
                base_url=base_url,
            )
            result["run_name"] = run.get("name", "unnamed")
            results.append(result)

    summary = summarize_eval_scores(
        [EvalResult(score=r["score"], metrics=r["metrics"]) for r in results]
    )

    return {"summary": summary, "results": results}


def save_results(payload: dict[str, Any], output_name: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / output_name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation experiments")
    parser.add_argument("--dataset", default="backend/eval_dataset.sample.json")
    parser.add_argument("--config", default="experiments/experiment_config.json")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = run_experiments(
        dataset_path=args.dataset,
        config_path=args.config,
        provider=args.provider,
        token=args.token,
        api_key=args.api_key,
        base_url=args.base_url,
    )

    output_name = args.output or f"experiment_{uuid.uuid4().hex[:8]}.json"
    path = save_results(result, output_name)
    print(f"Saved results to {path}")


if __name__ == "__main__":
    main()
