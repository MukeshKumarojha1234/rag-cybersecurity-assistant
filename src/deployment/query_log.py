"""SQLite-backed query logging — the "query + retrieval logging" half of node 8."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    query TEXT NOT NULL,
    blocked INTEGER NOT NULL,
    intent_category TEXT,
    confidence_score REAL,
    confidence_label TEXT,
    retrieved_doc_ids TEXT,
    citations TEXT,
    latency_ms REAL,
    model_name TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL
);
"""


@contextmanager
def _connect(db_path: Path | str | None = None):
    path = Path(db_path or config.LOG_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_query(
    query: str,
    blocked: bool,
    latency_ms: float,
    intent_category: str | None = None,
    confidence_score: float | None = None,
    confidence_label: str | None = None,
    retrieved_doc_ids: list[str] | None = None,
    citations: list[str] | None = None,
    model_name: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
    db_path: Path | str | None = None,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO query_log (
                created_at, query, blocked, intent_category, confidence_score, confidence_label,
                retrieved_doc_ids, citations, latency_ms, model_name, input_tokens, output_tokens, cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                query,
                int(blocked),
                intent_category,
                confidence_score,
                confidence_label,
                json.dumps(retrieved_doc_ids or []),
                json.dumps(citations or []),
                latency_ms,
                model_name,
                input_tokens,
                output_tokens,
                cost_usd,
            ),
        )


def recent_confidence_scores(limit: int, db_path: Path | str | None = None) -> list[float]:
    """Most recent non-null confidence scores, newest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT confidence_score FROM query_log WHERE confidence_score IS NOT NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [r[0] for r in rows]


def summary_stats(db_path: Path | str | None = None) -> dict:
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        blocked = conn.execute("SELECT COUNT(*) FROM query_log WHERE blocked = 1").fetchone()[0]
        avg_latency = conn.execute("SELECT AVG(latency_ms) FROM query_log").fetchone()[0]
        avg_confidence = conn.execute(
            "SELECT AVG(confidence_score) FROM query_log WHERE confidence_score IS NOT NULL"
        ).fetchone()[0]
        total_cost = conn.execute("SELECT SUM(cost_usd) FROM query_log WHERE cost_usd IS NOT NULL").fetchone()[0]

    return {
        "total_queries": total,
        "blocked_queries": blocked,
        "avg_latency_ms": avg_latency,
        "avg_confidence": avg_confidence,
        "total_cost_usd": total_cost or 0.0,
    }
