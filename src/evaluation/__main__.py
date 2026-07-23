"""CLI: `python -m src.evaluation` builds (or reuses) a reproducible eval corpus and scores it."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from src.embedding_indexing import HybridIndex, build_index
from src.generation.generator import AnthropicGenerator, StubGenerator
from src.preprocessing import preprocess_documents
from src.retrieval import CrossEncoderReranker

from . import config
from .golden_set import build_eval_corpus
from .pipeline import evaluate

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    try:
        index = HybridIndex.load(config.EVAL_INDEX_DIR)
        print(f"Loaded existing eval index ({len(index.chunks)} chunks) from {config.EVAL_INDEX_DIR}.")
    except FileNotFoundError:
        print("Building eval corpus (MITRE ATT&CK catalogue + internal SOPs + 2 pinned CVEs)...")
        docs = build_eval_corpus()
        chunks = preprocess_documents(docs)
        index = build_index(chunks)
        index.save(config.EVAL_INDEX_DIR)
        print(f"Built and saved eval index ({len(index.chunks)} chunks) to {config.EVAL_INDEX_DIR}.")

    reranker = CrossEncoderReranker()

    if os.environ.get("ANTHROPIC_API_KEY"):
        generator = AnthropicGenerator()
        print(f"Using AnthropicGenerator ({generator.model_name}).")
    else:
        generator = StubGenerator()
        print(
            "No ANTHROPIC_API_KEY set — using StubGenerator. Retrieval metrics below are unaffected "
            "and reliable, but generation metrics will be misleading: faithfulness will read ~0 (the "
            "stub's answer text is a generic placeholder, not real content) and citation_accuracy will "
            "read artificially high (it cites every retrieved chunk indiscriminately, including the "
            "correct one whenever retrieval succeeded)."
        )

    report = evaluate(index, reranker, generator)

    print("\n--- Retrieval ---")
    for r in report.retrieval:
        status = f"rank {r.hit_rank}" if r.hit_rank else "MISS"
        print(f"  [{status:>7}] recall={r.recall:.2f} precision={r.precision:.2f}  {r.query!r}")
    print(f"\nMean recall: {report.mean_recall:.2f}  Mean precision: {report.mean_precision:.2f}  MRR: {report.mrr:.3f}")

    print("\n--- Generation ---")
    for g in report.generation:
        print(
            f"  faithfulness={g.faithfulness:.2f} citation_correct={g.citation_correct} "
            f"blocked={g.blocked_unexpectedly}  {g.query!r}"
        )
        if g.keyword_misses:
            print(f"      missing keywords: {g.keyword_misses}")
    print(
        f"\nMean faithfulness: {report.mean_faithfulness:.2f}  "
        f"Citation accuracy: {report.citation_accuracy:.2f}  "
        f"False-block rate: {report.false_block_rate:.2f}"
    )
