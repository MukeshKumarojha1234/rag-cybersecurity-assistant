"""Node 1 entry point: fetch and normalize documents from every configured data source."""
from __future__ import annotations

import logging

from .base import DataSource
from .cve_nvd import CveNvdSource
from .ics_cert import IcsCertSource
from .internal_sop import InternalSopSource
from .mitre_attack import MitreAttackSource
from .models import RawDocument

logger = logging.getLogger(__name__)


def default_sources() -> list[DataSource]:
    return [
        CveNvdSource(),
        MitreAttackSource(),
        IcsCertSource(),
        InternalSopSource(),
    ]


def fetch_all(sources: list[DataSource] | None = None) -> list[RawDocument]:
    """Run every node-1 data source and return a combined, normalized document set.

    A failure in one source (e.g. a feed being temporarily down) doesn't stop
    the others — each is isolated and logged.
    """
    documents: list[RawDocument] = []
    for source in sources or default_sources():
        try:
            fetched = source.fetch()
            logger.info("%s: fetched %d documents", source.source_type, len(fetched))
            documents.extend(fetched)
        except Exception:
            logger.exception("Data source %s failed; continuing with the rest.", source.source_type)
    return documents
