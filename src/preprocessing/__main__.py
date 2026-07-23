"""CLI smoke test: `python -m src.preprocessing` runs node 1 then node 2."""
import logging
from collections import Counter

from src.data_sources import fetch_all

from .pipeline import preprocess_documents

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    docs = fetch_all()
    print(f"\nNode 1: fetched {len(docs)} raw documents.")

    chunks = preprocess_documents(docs)
    print(f"Node 2: produced {len(chunks)} chunks.")

    by_source = Counter(c.source_type for c in chunks)
    for source_type, count in by_source.items():
        print(f"  - {source_type}: {count} chunks")

    if chunks:
        sample = chunks[0]
        print("\nSample chunk:")
        print(f"  id={sample.id} section={sample.section} words={len(sample.text.split())}")
        print(f"  text preview: {sample.text[:200]!r}")
        print(f"  metadata: {sample.metadata}")
