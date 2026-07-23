"""CVE / NVD data source (node 1).

Pulls vulnerability records from the NVD CVE API v2.0
(https://nvd.nist.gov/developers/vulnerabilities), the authoritative
feed named in the workflow's "Data sources" node.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from . import config
from .base import DataSource
from .models import RawDocument


class CveNvdSource(DataSource):
    source_type = "cve_nvd"

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or config.NVD_API_KEY
        self.session = session or requests.Session()

    def fetch(
        self, *, published_since: timedelta = timedelta(days=7), results_per_page: int = 200
    ) -> list[RawDocument]:
        """Fetch CVEs published in the last `published_since` window (max 120 days per NVD)."""
        end = datetime.now(timezone.utc)
        start = end - published_since
        params = {
            "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": results_per_page,
        }
        payload = self._get(params)
        return [self._to_document(item["cve"]) for item in payload.get("vulnerabilities", [])]

    def fetch_by_id(self, cve_id: str) -> RawDocument | None:
        """Fetch a single CVE by ID, e.g. 'CVE-2021-44228'."""
        payload = self._get({"cveId": cve_id})
        vulnerabilities = payload.get("vulnerabilities", [])
        return self._to_document(vulnerabilities[0]["cve"]) if vulnerabilities else None

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"User-Agent": config.USER_AGENT}
        if self.api_key:
            headers["apiKey"] = self.api_key
        response = self.session.get(
            config.NVD_API_BASE_URL, params=params, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _to_document(cve: dict[str, Any]) -> RawDocument:
        cve_id = cve["id"]
        description = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), ""
        )

        cvss_data, severity = None, None
        metrics = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if metrics.get(key):
                entry = metrics[key][0]
                cvss_data = entry["cvssData"]
                severity = entry.get("baseSeverity") or cvss_data.get("baseSeverity")
                break

        references = [ref["url"] for ref in cve.get("references", [])]

        content_parts = [description]
        if cvss_data:
            content_parts.append(
                f"CVSS base score: {cvss_data.get('baseScore')} ({severity}). "
                f"Vector: {cvss_data.get('vectorString')}."
            )
        if references:
            content_parts.append("References: " + "; ".join(references[:5]))

        return RawDocument(
            id=cve_id,
            source_type="cve_nvd",
            title=cve_id,
            content="\n\n".join(part for part in content_parts if part),
            url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            published_at=_parse_dt(cve.get("published")),
            metadata={
                "cvss_score": cvss_data.get("baseScore") if cvss_data else None,
                "severity": severity,
                "vuln_status": cve.get("vulnStatus"),
                "references": references,
            },
        )


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
