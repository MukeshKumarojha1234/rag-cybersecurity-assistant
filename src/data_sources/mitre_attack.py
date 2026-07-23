"""MITRE ATT&CK data source (node 1).

Pulls the Enterprise ATT&CK technique catalogue from the official STIX 2.1
bundle published at https://github.com/mitre-attack/attack-stix-data, the
canonical machine-readable source for ATT&CK content.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from . import config
from .base import DataSource
from .models import RawDocument


class MitreAttackSource(DataSource):
    source_type = "mitre_attack"

    def __init__(self, stix_url: str | None = None, session: requests.Session | None = None):
        self.stix_url = stix_url or config.MITRE_ATTACK_STIX_URL
        self.session = session or requests.Session()

    def fetch(self, *, include_subtechniques: bool = True, include_deprecated: bool = False) -> list[RawDocument]:
        headers = {"User-Agent": config.USER_AGENT}
        # The bundle is ~50MB, so this gets a longer timeout than other sources.
        response = self.session.get(
            self.stix_url, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS * 4
        )
        response.raise_for_status()
        bundle = response.json()

        documents = []
        for obj in bundle.get("objects", []):
            if obj.get("type") != "attack-pattern":
                continue
            if obj.get("revoked") or (obj.get("x_mitre_deprecated") and not include_deprecated):
                continue
            if obj.get("x_mitre_is_subtechnique") and not include_subtechniques:
                continue
            doc = self._to_document(obj)
            if doc:
                documents.append(doc)
        return documents

    @staticmethod
    def _to_document(obj: dict[str, Any]) -> RawDocument | None:
        attack_ref = next(
            (ref for ref in obj.get("external_references", []) if ref.get("source_name") == "mitre-attack"),
            None,
        )
        if not attack_ref or not attack_ref.get("external_id"):
            return None

        technique_id = attack_ref["external_id"]
        tactics = [phase["phase_name"] for phase in obj.get("kill_chain_phases", [])]

        return RawDocument(
            id=technique_id,
            source_type="mitre_attack",
            title=f"{technique_id} — {obj.get('name')}",
            content=obj.get("description", ""),
            url=attack_ref.get("url"),
            published_at=_parse_dt(obj.get("created")),
            metadata={
                "tactics": tactics,
                "platforms": obj.get("x_mitre_platforms", []),
                "is_subtechnique": obj.get("x_mitre_is_subtechnique", False),
                "version": obj.get("x_mitre_version"),
            },
        )


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
