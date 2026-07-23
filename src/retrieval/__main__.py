"""CLI smoke test: `python -m src.retrieval` runs node 4 against the saved node 3 index."""
import logging

from src.data_sources import fetch_all
from src.embedding_indexing import HybridIndex, build_index
from src.preprocessing import preprocess_documents

from .cross_encoder import CrossEncoderReranker
from .filters import MetadataFilter
from .pipeline import retrieve


def _print_results(label: str, results) -> None:
    print(f"\n--- {label} ---")
    if not results:
        print("  (no results)")
    for r in results:
        print(
            f"  rerank={r.rerank_score:.3f} hybrid={r.hybrid_score:.4f} "
            f"[{r.chunk.source_type}] {r.chunk.id} — {r.chunk.title}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        index = HybridIndex.load()
        print(f"Loaded existing node 3 index ({len(index.chunks)} chunks) from disk.")
    except FileNotFoundError:
        docs = fetch_all()
        chunks = preprocess_documents(docs)
        index = build_index(chunks)
        index.save()
        print(f"Built and saved a new index ({len(index.chunks)} chunks).")

    reranker = CrossEncoderReranker()

    # Node 3's hybrid search missed T1566 (Phishing) entirely for this query
    # despite the doc containing "phishing" 7 times — re-ranking should fix it.
    _print_results(
        "Unfiltered: 'phishing initial access technique'",
        retrieve("phishing initial access technique", index, reranker, top_k=5),
    )

    _print_results(
        "Filtered to ICS-CERT only: 'remote code execution in operator console'",
        retrieve(
            "remote code execution in operator console",
            index,
            reranker,
            filters=MetadataFilter(source_types=["ics_cert"]),
            top_k=5,
        ),
    )

    _print_results(
        "Filtered to CRITICAL CVEs only: 'authentication bypass'",
        retrieve(
            "authentication bypass",
            index,
            reranker,
            filters=MetadataFilter(source_types=["cve_nvd"], min_severity="CRITICAL"),
            top_k=5,
        ),
    )
