"""Normalizes CVE/CVSS metadata fields to a consistent schema.

Node 1 already extracts these fields from the NVD API, but doesn't guarantee
their types/shape are safe to rely on downstream (e.g. a missing metric
block, or a score arriving as a string). This is the single place that
contract is enforced before chunks are indexed.
"""
from __future__ import annotations

from typing import Any

VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def normalize_cve_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(metadata)

    severity = normalized.get("severity")
    severity = severity.upper() if isinstance(severity, str) else None
    normalized["severity"] = severity if severity in VALID_SEVERITIES else None

    score = normalized.get("cvss_score")
    try:
        normalized["cvss_score"] = float(score) if score is not None else None
    except (TypeError, ValueError):
        normalized["cvss_score"] = None

    normalized["references"] = list(normalized.get("references") or [])
    normalized["vuln_status"] = normalized.get("vuln_status") or None

    return normalized
