"""ICS-CERT advisory data source (node 1).

Pulls CISA Industrial Control Systems advisories from CISA's public RSS
feed. CISA's site rejects requests without a browser-like User-Agent
header (403), so one is always sent.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from . import config
from .base import DataSource
from .models import RawDocument

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class IcsCertSource(DataSource):
    source_type = "ics_cert"

    def __init__(self, feed_url: str | None = None, session: requests.Session | None = None):
        self.feed_url = feed_url or config.ICS_CERT_FEED_URL
        self.session = session or requests.Session()

    def fetch(self, *, limit: int | None = None) -> list[RawDocument]:
        headers = {"User-Agent": config.USER_AGENT}
        response = self.session.get(self.feed_url, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = root.findall("./channel/item")
        if limit:
            items = items[:limit]
        return [self._to_document(item) for item in items]

    @staticmethod
    def _to_document(item: ET.Element) -> RawDocument:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()

        description = _TAG_RE.sub(" ", item.findtext("description") or "")
        description = _WHITESPACE_RE.sub(" ", description).strip()

        advisory_id = link.rstrip("/").rsplit("/", 1)[-1].upper() if link else title

        return RawDocument(
            id=advisory_id,
            source_type="ics_cert",
            title=title,
            content=description,
            url=link or None,
            published_at=_parse_rss_date(item.findtext("pubDate")),
            metadata={},
        )


def _parse_rss_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
