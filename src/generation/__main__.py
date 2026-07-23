"""CLI smoke test: `python -m src.generation` runs nodes 3-5 against the saved index."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from src.embedding_indexing import HybridIndex
from src.retrieval import CrossEncoderReranker, retrieve

from .generator import AnthropicGenerator, StubGenerator
from .pipeline import generate_answer

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    index = HybridIndex.load()
    print(f"Loaded node 3 index ({len(index.chunks)} chunks).")
    reranker = CrossEncoderReranker()

    if os.environ.get("ANTHROPIC_API_KEY"):
        generator = AnthropicGenerator()
        print(f"Using AnthropicGenerator ({generator.model_name}).")
    else:
        generator = StubGenerator()
        print(
            "No ANTHROPIC_API_KEY set — using StubGenerator (verifies wiring/citations only, "
            "not answer quality). Set the env var to see a real generated answer."
        )

    for query in ["What SOP applies to ransomware containment?", "What is CVSS scoring used for?"]:
        results = retrieve(query, index, reranker, top_k=5)
        answer = generate_answer(query, results, generator)

        print(f"\nQuery: {query!r}")
        print(f"Grounded: {answer.grounded} | context chunks: {answer.context_chunk_count}")
        print(f"Answer:\n{answer.answer}")
        print("Citations:")
        for c in answer.citations:
            print(f"  [{c.marker}] {c.source_type} {c.chunk_id} — {c.title}")
