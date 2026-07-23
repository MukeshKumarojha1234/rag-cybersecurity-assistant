"""The golden test set for node 7 — queries with known-correct answers.

Sources are chosen to be reproducible regardless of when this runs: MITRE
ATT&CK's technique catalogue and our own internal SOPs are always present
in full; CVEs are pinned by ID (fetch_by_id) rather than relying on node
1's fetch_all(), whose CVE window is a rolling last-7-days that would make
CVE-based examples flaky. ICS-CERT is a rotating feed with no stable
per-advisory guarantee, so it's excluded from the golden set entirely.
"""
from __future__ import annotations

from pydantic import BaseModel

from src.data_sources.cve_nvd import CveNvdSource
from src.data_sources.internal_sop import InternalSopSource
from src.data_sources.mitre_attack import MitreAttackSource
from src.data_sources.models import RawDocument
from src.retrieval.filters import MetadataFilter

from . import config


class GoldenExample(BaseModel):
    query: str
    relevant_doc_ids: list[str]  # doc_id values expected among the retrieved results
    expected_keywords: list[str]  # substrings a faithful answer should contain
    filters: MetadataFilter | None = None


GOLDEN_SET: list[GoldenExample] = [
    GoldenExample(
        query="What SOP applies to ransomware containment?",
        relevant_doc_ids=["sop-ir-014-ransomware-containment"],
        expected_keywords=["isolate", "network"],
    ),
    GoldenExample(
        query="What is phishing as an ATT&CK technique?",
        relevant_doc_ids=["T1566"],
        expected_keywords=["phishing", "social engineering"],
    ),
    GoldenExample(
        query="What does the Data Encrypted for Impact technique describe?",
        relevant_doc_ids=["T1486"],
        expected_keywords=["encrypt"],
    ),
    GoldenExample(
        query="What tactic does the Command and Scripting Interpreter technique belong to?",
        relevant_doc_ids=["T1059"],
        expected_keywords=["script"],
    ),
    GoldenExample(
        query="What vulnerability does CVE-2021-44228 describe?",
        relevant_doc_ids=["CVE-2021-44228"],
        expected_keywords=["log4j", "jndi"],
    ),
    GoldenExample(
        query="What does CVE-2017-0144 affect?",
        relevant_doc_ids=["CVE-2017-0144"],
        expected_keywords=["smb"],
    ),
]


def build_eval_corpus() -> list[RawDocument]:
    """Build a reproducible corpus covering every GOLDEN_SET reference doc.

    Includes the full MITRE ATT&CK catalogue as a realistic-scale pool of
    distractors — without them, retrieval metrics would be trivially
    perfect and wouldn't validate much.
    """
    docs: list[RawDocument] = []
    docs.extend(MitreAttackSource().fetch())
    docs.extend(InternalSopSource().fetch())

    cve_source = CveNvdSource()
    for cve_id in config.PINNED_CVE_IDS:
        doc = cve_source.fetch_by_id(cve_id)
        if doc:
            docs.append(doc)

    return docs
