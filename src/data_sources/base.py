"""Common interface every node-1 data source implements."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import RawDocument


class DataSource(ABC):
    """A single ingestion source that produces normalized RawDocuments."""

    source_type: str

    @abstractmethod
    def fetch(self, **kwargs) -> list[RawDocument]:
        """Fetch and normalize documents from this source."""
