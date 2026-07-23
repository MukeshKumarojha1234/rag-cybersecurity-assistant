"""CLI smoke test: `python -m src.data_sources` fetches from every node-1 source."""
import logging

from .registry import fetch_all

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    docs = fetch_all()
    print(f"\nFetched {len(docs)} raw documents total.")
    for doc in docs[:5]:
        print(f"- [{doc.source_type}] {doc.id}: {doc.title}")
