from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import db
from backend.evaluation import evaluate_report, load_eval_dataset, summarize_eval_scores
from backend.pipeline import build_outline, compress_source, synthesize_report
from backend.retrieval import enhanced_retrieve

app = FastAPI(title="Web Info Collector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def env_default(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value else default


class ReportRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    lang: str = "zh"
    min_sources: int = 3
    max_results: int = 8
    max_pages: int = 5
    allow_domains: list[str] | None = None
    block_domains: list[str] | None = None
    model_id: str | None = None
    provider: str | None = None
    token: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    compress_model_id: str | None = None
    outline_model_id: str | None = None
    report_model_id: str | None = None


class ReportResponse(BaseModel):
    id: str
    status: str


class ReportDetail(BaseModel):
    id: str
    topic: str
    created_at: str
    status: str
    model_id: str | None
    provider: str | None
    summary_md: str | None = None
    sources: list[dict[str, Any]] | None = None
    stages: dict[str, Any] | None = None
    error: str | None = None
    params: dict[str, Any] | None = None


class EvalJudgeConfig(BaseModel):
    model_id: str
    provider: str | None = None
    token: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class EvalRequest(BaseModel):
    report_id: str | None = None
    topic: str | None = None
    summary_md: str | None = None
    sources: list[dict[str, Any]] | None = None
    min_sources: int = 3
    judge: EvalJudgeConfig | None = None


class EvalResponse(BaseModel):
    id: str
    status: str


class EvalDetail(BaseModel):
    id: str
    report_id: str | None = None
    created_at: str
    status: str
    score: float | None = None
    metrics: dict[str, Any] | None = None
    judge_feedback: str | None = None
    error: str | None = None


class BatchEvalRequest(BaseModel):
    dataset_path: str
    judge: EvalJudgeConfig | None = None
    provider: str | None = None
    token: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class BatchEvalResponse(BaseModel):
    id: str
    status: str
    summary: dict[str, Any] | None = None


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}



def _resolve_model(payload: ReportRequest, stage: str) -> str:
    if stage == "compress" and payload.compress_model_id:
        return payload.compress_model_id
    if stage == "outline" and payload.outline_model_id:
        return payload.outline_model_id
    if stage == "report" and payload.report_model_id:
        return payload.report_model_id
    return payload.model_id or env_default("SMOLAGENTS_MODEL_ID") or "Qwen/Qwen3-Next-80B-A3B-Thinking"



def _run_report(report_id: str, payload: ReportRequest) -> None:
    stages: dict[str, Any] = {}
    try:
        sources = enhanced_retrieve(
            payload.topic,
            max_results=payload.max_results,
            max_pages=payload.max_pages,
            allow_domains=payload.allow_domains,
            block_domains=payload.block_domains,
        )
        stages["retrieval"] = {"sources": len(sources)}

        evidence_outputs = []
        for src in sources:
            evidence = compress_source(
                topic=payload.topic,
                source=src,
                model_id=_resolve_model(payload, "compress"),
                provider=payload.provider or env_default("SMOLAGENTS_PROVIDER"),
                token=payload.token or env_default("HF_TOKEN") or env_default("HUGGINGFACEHUB_API_TOKEN"),
                api_key=payload.api_key or env_default("HF_API_KEY"),
                base_url=payload.base_url or env_default("HF_BASE_URL"),
            )
            src["evidence"] = evidence
            evidence_outputs.append(evidence)
        stages["compression"] = {"items": len(evidence_outputs)}

        outline = build_outline(
            topic=payload.topic,
            evidence=evidence_outputs,
            model_id=_resolve_model(payload, "outline"),
            provider=payload.provider or env_default("SMOLAGENTS_PROVIDER"),
            token=payload.token or env_default("HF_TOKEN") or env_default("HUGGINGFACEHUB_API_TOKEN"),
            api_key=payload.api_key or env_default("HF_API_KEY"),
            base_url=payload.base_url or env_default("HF_BASE_URL"),
            lang=payload.lang,
        )
        stages["outline"] = outline

        summary = synthesize_report(
            topic=payload.topic,
            evidence=evidence_outputs,
            outline=outline,
            model_id=_resolve_model(payload, "report"),
            provider=payload.provider or env_default("SMOLAGENTS_PROVIDER"),
            token=payload.token or env_default("HF_TOKEN") or env_default("HUGGINGFACEHUB_API_TOKEN"),
            api_key=payload.api_key or env_default("HF_API_KEY"),
            base_url=payload.base_url or env_default("HF_BASE_URL"),
            lang=payload.lang,
            min_sources=payload.min_sources,
        )
        stages["report"] = {"length": len(summary)}

        db.update_report(report_id, status="completed", summary_md=summary, sources=sources, stages=stages)
    except Exception as exc:  # noqa: BLE001
        db.update_report(report_id, status="failed", stages=stages, error=str(exc))


@app.post("/api/reports", response_model=ReportResponse)
def create_report(payload: ReportRequest, background_tasks: BackgroundTasks) -> ReportResponse:
    report_id = str(uuid.uuid4())
    db.create_report(
        report_id,
        payload.topic,
        payload.model_id or env_default("SMOLAGENTS_MODEL_ID"),
        payload.provider or env_default("SMOLAGENTS_PROVIDER"),
        params=payload.model_dump(),
    )
    background_tasks.add_task(_run_report, report_id, payload)
    return ReportResponse(id=report_id, status="running")


@app.get("/api/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: str) -> ReportDetail:
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportDetail(**report)


@app.get("/api/reports", response_model=list[ReportDetail])
def list_reports(limit: int = 20) -> list[ReportDetail]:
    return [ReportDetail(**item) for item in db.list_reports(limit=limit)]



def _run_eval(eval_id: str, payload: EvalRequest) -> None:
    try:
        if payload.report_id:
            report = db.get_report(payload.report_id)
            if not report:
                raise ValueError("Report not found")
            topic = report["topic"]
            summary_md = report.get("summary_md")
            sources = report.get("sources") or []
        else:
            if not payload.topic or not payload.summary_md:
                raise ValueError("topic and summary_md are required when report_id is not provided")
            topic = payload.topic
            summary_md = payload.summary_md
            sources = payload.sources or []

        judge_cfg = payload.judge.model_dump() if payload.judge else None
        result = evaluate_report(
            topic=topic,
            summary_md=summary_md or "",
            sources=sources,
            min_sources=payload.min_sources,
            judge=judge_cfg,
        )
        db.update_eval(
            eval_id,
            status="completed",
            score=result.score,
            metrics=result.metrics,
            judge_feedback=result.judge_feedback,
        )
    except Exception as exc:  # noqa: BLE001
        db.update_eval(eval_id, status="failed", error=str(exc))


@app.post("/api/evals", response_model=EvalResponse)
def create_eval(payload: EvalRequest, background_tasks: BackgroundTasks) -> EvalResponse:
    eval_id = str(uuid.uuid4())
    db.create_eval(eval_id, payload.report_id)
    background_tasks.add_task(_run_eval, eval_id, payload)
    return EvalResponse(id=eval_id, status="running")


@app.get("/api/evals/{eval_id}", response_model=EvalDetail)
def get_eval(eval_id: str) -> EvalDetail:
    eval_item = db.get_eval(eval_id)
    if not eval_item:
        raise HTTPException(status_code=404, detail="Eval not found")
    return EvalDetail(**eval_item)


@app.get("/api/evals", response_model=list[EvalDetail])
def list_evals(limit: int = 20) -> list[EvalDetail]:
    return [EvalDetail(**item) for item in db.list_evals(limit=limit)]


@app.post("/api/evals/batch", response_model=BatchEvalResponse)
def batch_eval(payload: BatchEvalRequest, background_tasks: BackgroundTasks) -> BatchEvalResponse:
    batch_id = str(uuid.uuid4())

    def _run_batch() -> None:
        try:
            dataset = load_eval_dataset(payload.dataset_path)
            results = []
            for item in dataset:
                req = ReportRequest(
                    topic=item["topic"],
                    lang=item.get("lang", "zh"),
                    min_sources=item.get("min_sources", 3),
                    max_results=item.get("max_results", 8),
                    max_pages=item.get("max_pages", 5),
                    model_id=item.get("model_id"),
                    provider=payload.provider,
                    token=payload.token,
                    api_key=payload.api_key,
                    base_url=payload.base_url,
                )
                # Run report synchronously for batch
                tmp_id = str(uuid.uuid4())
                db.create_report(tmp_id, req.topic, req.model_id, req.provider, params=req.model_dump())
                _run_report(tmp_id, req)
                report = db.get_report(tmp_id)
                if not report:
                    continue
                judge_cfg = payload.judge.model_dump() if payload.judge else None
                result = evaluate_report(
                    topic=report["topic"],
                    summary_md=report.get("summary_md") or "",
                    sources=report.get("sources") or [],
                    min_sources=req.min_sources,
                    judge=judge_cfg,
                )
                results.append(result)
            summary = summarize_eval_scores(results)
            db.update_eval(batch_id, status="completed", score=summary.get("avg_score", 0.0), metrics=summary)
        except Exception as exc:  # noqa: BLE001
            db.update_eval(batch_id, status="failed", error=str(exc))

    db.create_eval(batch_id, report_id=None)
    background_tasks.add_task(_run_batch)
    return BatchEvalResponse(id=batch_id, status="running")
