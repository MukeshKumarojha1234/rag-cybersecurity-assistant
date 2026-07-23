"""Node 2 — Preprocessing & chunking.

Cleans raw documents from node 1, normalizes CVE/CVSS fields, chunks each
document by source type, and tags every chunk with metadata — producing the
units that node 3 (embedding & indexing) will embed and index.
"""
from .models import Chunk
from .pipeline import preprocess_document, preprocess_documents

__all__ = ["Chunk", "preprocess_document", "preprocess_documents"]
