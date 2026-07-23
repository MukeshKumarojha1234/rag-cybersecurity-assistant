"""Node 1 — Data sources.

Fetches and normalizes raw documents from CVE/NVD feeds, MITRE ATT&CK,
ICS-CERT advisories, and internal SOPs, handing off a unified list of
RawDocument to node 2 (preprocessing & chunking).
"""
from .base import DataSource
from .models import RawDocument
from .registry import default_sources, fetch_all

__all__ = ["DataSource", "RawDocument", "default_sources", "fetch_all"]
