"""CLI smoke test: `python -m src.embedding_indexing` runs nodes 1-3 and does a sample search."""
import logging

from src.data_sources import fetch_all
from src.preprocessing import preprocess_documents

from . import config
from .pipeline import build_index

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    docs = fetch_all()
    chunks = preprocess_documents(docs)
    print(f"\nNode 1+2: {len(docs)} documents -> {len(chunks)} chunks.")

    index = build_index(chunks)
    print(f"Node 3: indexed {len(index.chunks)} chunks ({index.vector_index.embeddings.shape[1]}-dim embeddings).")

    index.save()
    print(f"Saved index to {config.INDEX_DIR}")

    for query in ["log4j remote code execution", "ransomware containment steps", "phishing initial access technique"]:
        print(f"\nQuery: {query!r}")
        for result in index.search(query, top_k=3):
            print(
                f"  [{result.chunk.source_type}] {result.chunk.id} "
                f"(fused={result.score:.4f} vec={result.vector_score} bm25={result.keyword_score}) "
                f"— {result.chunk.title}"
            )
