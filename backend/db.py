import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("data") / "app.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                model_id TEXT,
                provider TEXT,
                params_json TEXT,
                sources_json TEXT,
                summary_md TEXT,
                error TEXT
            )
            """
        )
        _ensure_columns(
            conn,
            "reports",
            {
                "stages_json": "TEXT",
            },
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evals (
                id TEXT PRIMARY KEY,
                report_id TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL,
                metrics_json TEXT,
                judge_feedback TEXT,
                error TEXT,
                FOREIGN KEY(report_id) REFERENCES reports(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_report(report_id: str, topic: str, model_id: str | None, provider: str | None, params: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO reports (id, topic, created_at, status, model_id, provider, params_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                topic,
                datetime.utcnow().isoformat() + "Z",
                "running",
                model_id,
                provider,
                json.dumps(params, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_report(
    report_id: str,
    *,
    status: str,
    summary_md: str | None = None,
    sources: list[dict[str, Any]] | None = None,
    stages: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE reports
            SET status = ?, summary_md = ?, sources_json = ?, stages_json = ?, error = ?
            WHERE id = ?
            """,
            (
                status,
                summary_md,
                json.dumps(sources, ensure_ascii=False) if sources is not None else None,
                json.dumps(stages, ensure_ascii=False) if stages is not None else None,
                error,
                report_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_report(report_id: str) -> dict[str, Any] | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("params_json"):
            data["params"] = json.loads(data.pop("params_json"))
        if data.get("sources_json"):
            data["sources"] = json.loads(data.pop("sources_json"))
        if data.get("stages_json"):
            data["stages"] = json.loads(data.pop("stages_json"))
        return data
    finally:
        conn.close()


def list_reports(limit: int = 20) -> list[dict[str, Any]]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            if item.get("params_json"):
                item["params"] = json.loads(item.pop("params_json"))
            if item.get("sources_json"):
                item["sources"] = json.loads(item.pop("sources_json"))
            if item.get("stages_json"):
                item["stages"] = json.loads(item.pop("stages_json"))
            data.append(item)
        return data
    finally:
        conn.close()


def create_eval(eval_id: str, report_id: str | None) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO evals (id, report_id, created_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                eval_id,
                report_id,
                datetime.utcnow().isoformat() + "Z",
                "running",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_eval(
    eval_id: str,
    *,
    status: str,
    score: float | None = None,
    metrics: dict[str, Any] | None = None,
    judge_feedback: str | None = None,
    error: str | None = None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE evals
            SET status = ?, score = ?, metrics_json = ?, judge_feedback = ?, error = ?
            WHERE id = ?
            """,
            (
                status,
                score,
                json.dumps(metrics, ensure_ascii=False) if metrics is not None else None,
                judge_feedback,
                error,
                eval_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_eval(eval_id: str) -> dict[str, Any] | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM evals WHERE id = ?", (eval_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("metrics_json"):
            data["metrics"] = json.loads(data.pop("metrics_json"))
        return data
    finally:
        conn.close()


def list_evals(limit: int = 20) -> list[dict[str, Any]]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM evals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            if item.get("metrics_json"):
                item["metrics"] = json.loads(item.pop("metrics_json"))
            data.append(item)
        return data
    finally:
        conn.close()
