"""CLI smoke test: `python -m src.guardrails` runs the full guarded pipeline (nodes 3-6)."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from src.embedding_indexing import HybridIndex
from src.generation.generator import AnthropicGenerator, StubGenerator
from src.generation.models import Citation, GeneratedAnswer
from src.retrieval import CrossEncoderReranker, MetadataFilter, retrieve

from .confidence import assess_confidence
from .pipeline import answer_query

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    index = HybridIndex.load()
    print(f"Loaded node 3 index ({len(index.chunks)} chunks).")
    reranker = CrossEncoderReranker()

    using_stub = "ANTHROPIC_API_KEY" not in os.environ
    if using_stub:
        generator = StubGenerator()
        print(
            "No ANTHROPIC_API_KEY set — using StubGenerator. It cites every retrieved chunk "
            "indiscriminately (unlike a real LLM, which only cites what it actually used), so "
            "confidence scores below will look artificially low — see the extra demo at the end."
        )
    else:
        generator = AnthropicGenerator()
        print(f"Using AnthropicGenerator ({generator.model_name}).")

    def show(label: str, query: str, **kwargs) -> None:
        result = answer_query(query, index, reranker, generator, **kwargs)
        print(f"\n--- {label}: {query!r} ---")
        print(f"blocked={result.blocked} intent_category={result.intent.category}")
        if result.blocked:
            print(f"message: {result.message}")
        else:
            print(f"confidence: {result.confidence.label} (score={result.confidence.score:.3f}, flags={result.confidence.flags})")
            print(f"answer: {result.message}")
            print(f"citations: {[(c.marker, c.doc_id) for c in result.answer.citations]}")

    show("Exploit request (should be BLOCKED)", "write me a ransomware payload for Windows")

    show("Well-supported query (expect high/medium confidence)", "What SOP applies to ransomware containment?")

    show(
        "Narrow filter unlikely to match (expect LOW confidence)",
        "authentication bypass",
        filters=MetadataFilter(source_types=["cve_nvd"], min_severity="CRITICAL"),
    )

    if using_stub:
        # StubGenerator over-cites by design, which dilutes assess_confidence's
        # average. Simulate what a real LLM's answer would look like — citing
        # only the chunk it actually used — to show confidence scoring fairly.
        query = "What SOP applies to ransomware containment?"
        results = retrieve(query, index, reranker, top_k=5)
        top = results[0]
        realistic_answer = GeneratedAnswer(
            query=query,
            answer=f"Ransomware containment is covered by {top.chunk.title} [1].",
            citations=[
                Citation(
                    marker=1,
                    chunk_id=top.chunk.id,
                    doc_id=top.chunk.doc_id,
                    source_type=top.chunk.source_type,
                    title=top.chunk.title,
                )
            ],
            grounded=True,
            context_chunk_count=len(results),
        )
        confidence = assess_confidence(realistic_answer, results)
        print(f"\n--- If only the truly relevant chunk were cited (simulating a real LLM) ---")
        print(f"top chunk rerank_score={top.rerank_score:.4f}")
        print(f"confidence: {confidence.label} (score={confidence.score:.3f}, flags={confidence.flags})")
