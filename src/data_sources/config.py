"""Node 1 configuration — all values overridable via environment variables."""
import os
from pathlib import Path

# NVD CVE API v2.0 — https://nvd.nist.gov/developers/vulnerabilities
NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.environ.get("NVD_API_KEY")  # optional; raises the rate limit from 5 to 50 req/30s

# Official STIX 2.1 bundle — https://github.com/mitre-attack/attack-stix-data
MITRE_ATTACK_STIX_URL = os.environ.get(
    "MITRE_ATTACK_STIX_URL",
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json",
)

# CISA ICS advisories RSS feed. CISA rejects requests without a
# browser-like User-Agent (403), so USER_AGENT below is always sent.
ICS_CERT_FEED_URL = os.environ.get(
    "ICS_CERT_FEED_URL",
    "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml",
)

# Local directory of internal SOP documents (.md, .txt, .pdf, .docx).
INTERNAL_SOP_DIR = Path(
    os.environ.get("INTERNAL_SOP_DIR", Path(__file__).resolve().parents[2] / "data" / "sops")
)

REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "SentinelRAG-DataIngestion/1.0 (+cybersecurity-assistant; contact: security-team)"
