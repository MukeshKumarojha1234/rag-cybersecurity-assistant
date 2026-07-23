"""Node 8 entry point: the FastAPI app the frontend's app.js already expects at /api/query."""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.embedding_indexing import HybridIndex
from src.generation import config as generation_config
from src.generation.generator import AnthropicGenerator, GroqGenerator, StubGenerator
from src.guardrails import HeuristicIntentClassifier, answer_query
from src.retrieval import CrossEncoderReranker, MetadataFilter

from . import config
from .ad_hoc import build_ad_hoc_chunks
from .cost import estimate_cost_usd
from .monitoring import check_drift
from .query_log import log_query, summary_stats

logger = logging.getLogger(__name__)

_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading hybrid index...")
    _state["index"] = HybridIndex.load()
    logger.info("Loading cross-encoder reranker...")
    _state["reranker"] = CrossEncoderReranker()
    _state["classifier"] = HeuristicIntentClassifier()

    if os.environ.get("ANTHROPIC_API_KEY"):
        _state["generator"] = AnthropicGenerator()
        logger.info("Using AnthropicGenerator (%s).", _state["generator"].model_name)
    elif os.environ.get("GROQ_API_KEY"):
        _state["generator"] = GroqGenerator()
        logger.info("Using GroqGenerator (%s).", _state["generator"].model_name)
    else:
        _state["generator"] = StubGenerator()
        logger.warning("No ANTHROPIC_API_KEY or GROQ_API_KEY set — using StubGenerator. Answers will be placeholders.")

    yield
    _state.clear()


app = FastAPI(title="SentinelRAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    index = _state.get("index")
    return {
        "status": "ok" if index is not None else "starting",
        "index_chunks": len(index.chunks) if index else 0,
        "generator": _state["generator"].model_name if "generator" in _state else None,
    }


@app.get("/api/stats")
async def stats():
    drift = check_drift(_state["index"])
    return {**summary_stats(), "drift": drift.model_dump()}


@app.post("/api/query")
async def query_endpoint(request: Request):
    start = time.monotonic()
    content_type = request.headers.get("content-type", "")
    ad_hoc_chunks: list = []
    upload_status: dict | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        query_text = str(form.get("query", ""))
        source_labels = _parse_sources(form.get("sources"))
        response_length = form.get("responseLength")
        upload = form.get("file")
        if upload is not None and hasattr(upload, "filename") and upload.filename:
            file_bytes = await upload.read()
            if len(file_bytes) > config.MAX_UPLOAD_BYTES:
                return JSONResponse(status_code=413, content={"error": "file too large"})
            outcome = build_ad_hoc_chunks(upload.filename, file_bytes)
            ad_hoc_chunks = outcome.chunks
            upload_status = {"filename": upload.filename, "status": outcome.status, "cited": False}
    else:
        payload = await request.json()
        query_text = str(payload.get("query", ""))
        source_labels = payload.get("sources")
        response_length = payload.get("responseLength")

    query_text = query_text.strip()
    if not query_text:
        return JSONResponse(status_code=400, content={"error": "query is required"})

    filters = _build_filters(source_labels)
    max_tokens = _resolve_max_tokens(response_length)

    result = answer_query(
        query_text,
        _state["index"],
        _state["reranker"],
        _state["generator"],
        filters=filters,
        classifier=_state["classifier"],
        extra_chunks=ad_hoc_chunks or None,
        max_tokens=max_tokens,
    )

    latency_ms = (time.monotonic() - start) * 1000

    if result.blocked:
        log_query(query_text, blocked=True, latency_ms=latency_ms, intent_category=result.intent.category)
        return {
            "text": result.message,
            "citations": [],
            "confidence": None,
            "blocked": True,
            "flagged": False,
            "upload": upload_status,
        }

    if upload_status is not None:
        upload_status["cited"] = any(c.doc_id == upload_status["filename"] for c in result.answer.citations)

    generator = _state["generator"]
    usage = getattr(generator, "last_usage", None) or {}
    cost = estimate_cost_usd(generator.model_name, usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    log_query(
        query_text,
        blocked=False,
        latency_ms=latency_ms,
        intent_category=result.intent.category,
        confidence_score=result.confidence.score,
        confidence_label=result.confidence.label,
        citations=[c.doc_id for c in result.answer.citations],
        model_name=generator.model_name,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        cost_usd=cost,
    )

    return {
        "text": result.message,
        "citations": [{"id": c.doc_id} for c in result.answer.citations],
        "confidence": result.confidence.score,
        "blocked": False,
        "flagged": result.confidence.label == "low",
        "upload": upload_status,
    }


def _resolve_max_tokens(response_length) -> int | None:
    """Map the frontend's 1-5 response-length slider to max_tokens for this call.

    Returns None (generator falls back to its own configured default) for a
    missing, non-numeric, or out-of-range value rather than raising — the
    slider is a UX nicety, not something a malformed value should break the
    query over.
    """
    try:
        level = int(response_length)
    except (TypeError, ValueError):
        return None
    return generation_config.RESPONSE_LENGTH_MAX_TOKENS.get(level)


def _parse_sources(raw) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [raw]
    return raw


def _build_filters(source_labels: list[str] | None) -> MetadataFilter | None:
    if not source_labels:
        return None
    mapped = [
        config.FRONTEND_SOURCE_LABELS[label] for label in source_labels if label in config.FRONTEND_SOURCE_LABELS
    ]
    return MetadataFilter(source_types=mapped) if mapped else None
