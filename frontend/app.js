// ---------------------------------------------------------------------------
// SentinelRAG frontend
//
// Talks to the FastAPI backend (src/deployment/api.py) at API_ENDPOINT,
// served from the same origin via server.py. Set USE_MOCK_PIPELINE to true
// to fall back to a local simulation of the 8-node pipeline instead (useful
// for UI-only work with no backend running).
// ---------------------------------------------------------------------------

const API_ENDPOINT = "/api/query";
const USE_MOCK_PIPELINE = false;

// --- DOM refs ---------------------------------------------------------------
const messagesEl = document.getElementById("messages");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const pipelineList = document.getElementById("pipelineList");
const pipelineStageLabel = document.getElementById("pipelineStageLabel");
const sourcesList = document.getElementById("sourcesList");
const confidenceBlock = document.getElementById("confidenceBlock");
const confidenceFill = document.getElementById("confidenceFill");
const confidenceValue = document.getElementById("confidenceValue");
const confidenceSlider = document.getElementById("confidenceSlider");
const confidenceTurnLabel = document.getElementById("confidenceTurnLabel");
const confidenceQueryLabel = document.getElementById("confidenceQueryLabel");
const connectionStatus = document.getElementById("connectionStatus");
const sourceToggles = document.querySelectorAll(".source-toggle");
const sidebar = document.getElementById("sidebar");
const sourcesPanel = document.getElementById("sourcesPanel");
const newChatBtn = document.getElementById("newChatBtn");
const attachBtn = document.getElementById("attachBtn");
const fileInput = document.getElementById("fileInput");
const attachedChip = document.getElementById("attachedChip");
const attachedFileName = document.getElementById("attachedFileName");
const attachedFileSize = document.getElementById("attachedFileSize");
const removeFileBtn = document.getElementById("removeFileBtn");
const responseLengthSlider = document.getElementById("responseLengthSlider");
const responseLengthValue = document.getElementById("responseLengthValue");

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const READABLE_TEXT_EXT = [".txt", ".md", ".csv", ".log"];

// 1-5 scale sent to the backend as "responseLength"; the API maps it to
// max_tokens (see src/generation/config.py's RESPONSE_LENGTH_MAX_TOKENS).
const RESPONSE_LENGTH_LABELS = { 1: "Short", 2: "Brief", 3: "Balanced", 4: "Thorough", 5: "Detailed" };
let responseLength = Number(responseLengthSlider.value);

responseLengthSlider.addEventListener("input", () => {
  responseLength = Number(responseLengthSlider.value);
  responseLengthValue.textContent = RESPONSE_LENGTH_LABELS[responseLength];
});

// --- Mock knowledge base -----------------------------------------------------
const MOCK_KB = [
  {
    tag: "CVE/NVD", tagClass: "tag-cve", id: "CVE-2024-3094",
    title: "CVE-2024-3094 — XZ Utils backdoor",
    text: "A malicious backdoor was introduced into liblzma versions 5.6.0 and 5.6.1, allowing remote code execution via crafted SSH certificate data under sshd.",
    keywords: ["xz", "backdoor", "liblzma", "ssh", "rce", "supply chain"]
  },
  {
    tag: "CVE/NVD", tagClass: "tag-cve", id: "CVE-2021-44228",
    title: "CVE-2021-44228 — Log4Shell",
    text: "Apache Log4j2 JNDI lookup features do not protect against attacker-controlled LDAP and other JNDI endpoints, enabling remote code execution.",
    keywords: ["log4j", "log4shell", "jndi", "rce", "java"]
  },
  {
    tag: "MITRE ATT&CK", tagClass: "tag-mitre", id: "T1566",
    title: "T1566 — Phishing",
    text: "Adversaries send phishing messages to gain access to victim systems, including spearphishing attachments, links, and via third-party services.",
    keywords: ["phishing", "spearphishing", "email", "initial access"]
  },
  {
    tag: "MITRE ATT&CK", tagClass: "tag-mitre", id: "T1059",
    title: "T1059 — Command and Scripting Interpreter",
    text: "Adversaries abuse command and script interpreters (PowerShell, cmd, bash) to execute commands, scripts, or binaries during post-exploitation.",
    keywords: ["powershell", "script", "command", "execution", "bash"]
  },
  {
    tag: "ICS-CERT", tagClass: "tag-ics", id: "ICSA-24-107-01",
    title: "ICSA-24-107-01 — SCADA HMI advisory",
    text: "Improper input validation in a SCADA HMI web interface allows an unauthenticated attacker to perform remote code execution on the operator console.",
    keywords: ["scada", "ics", "hmi", "plc", "operational technology", "ot"]
  },
  {
    tag: "Internal SOP", tagClass: "tag-sop", id: "SOP-IR-014",
    title: "SOP-IR-014 — Ransomware containment procedure",
    text: "On suspected ransomware activity: isolate affected hosts from the network, preserve volatile memory, notify the IR lead, and do not power off encrypted systems.",
    keywords: ["ransomware", "containment", "incident response", "isolate"]
  },
  {
    tag: "Internal SOP", tagClass: "tag-sop", id: "SOP-VM-002",
    title: "SOP-VM-002 — Critical CVE patch SLA",
    text: "Critical severity CVEs (CVSS >= 9.0) affecting internet-facing assets must be patched or mitigated within 72 hours of disclosure per internal policy.",
    keywords: ["patch", "sla", "cvss", "vulnerability management"]
  }
];

const EXPLOIT_KEYWORDS = [
  "write me a", "write an exploit", "generate malware", "build ransomware",
  "how do i hack", "how to hack", "create a virus", "bypass antivirus",
  "step by step attack", "reverse shell payload for", "weaponize"
];

// --- State --------------------------------------------------------------
let isBusy = false;
let attachedFile = null; // { file, name, size, textContent } | null

// --- Pipeline visualization ----------------------------------------------
const STAGES = ["ingest", "chunk", "index", "retrieve", "generate", "guardrail", "eval", "deploy"];

function resetPipeline() {
  pipelineList.querySelectorAll("li").forEach(li => li.classList.remove("active", "done", "blocked"));
}

function markStage(stage, status) {
  const li = pipelineList.querySelector(`[data-stage="${stage}"]`);
  if (!li) return;
  li.classList.remove("active", "done", "blocked");
  li.classList.add(status);
}

function setStageLabel(text) {
  pipelineStageLabel.textContent = text;
}

async function runStageAnimation(stage, label, ms) {
  markStage(stage, "active");
  setStageLabel(label);
  await sleep(ms);
  markStage(stage, "done");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// --- Rendering ------------------------------------------------------------
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function appendUserMessage(text, fileMeta) {
  const wrap = document.createElement("div");
  wrap.className = "message user";
  const fileChipHtml = fileMeta
    ? `<div class="message-file-chip"><span class="file-icon">📄</span><span class="file-name">${escapeHtml(fileMeta.name)}</span></div>`
    : "";
  wrap.innerHTML = `
    <div class="avatar user-avatar">U</div>
    <div class="bubble">${fileChipHtml}<p></p></div>
  `;
  wrap.querySelector("p").textContent = text;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function appendTypingIndicator() {
  const wrap = document.createElement("div");
  wrap.className = "message assistant";
  wrap.id = "typingMessage";
  wrap.innerHTML = `
    <div class="avatar assistant-avatar">S</div>
    <div class="bubble">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typingMessage");
  if (el) el.remove();
}

function uploadBadgeHtml(upload) {
  if (!upload) return "";
  const name = escapeHtml(upload.filename);
  if (upload.status === "unreadable") {
    return `<span class="badge badge-upload-warn" title="Couldn't extract text from this file (unsupported type or a corrupt/unparseable file) — it was ignored for this answer.">⚠ ${name} — unreadable, ignored</span>`;
  }
  if (upload.status === "empty") {
    return `<span class="badge badge-upload-warn" title="The file parsed but contained no extractable text — it was ignored for this answer.">⚠ ${name} — no text found, ignored</span>`;
  }
  if (upload.cited) {
    return `<span class="badge badge-upload-ok" title="This file was chunked, scored against your question, and at least one excerpt from it was cited in the answer below.">📄 ${name} — used in this answer</span>`;
  }
  return `<span class="badge" title="This file was chunked and scored against your question, but the model didn't end up citing it — the indexed corpus was judged more relevant.">📄 ${name} — read, not cited</span>`;
}

function appendAssistantMessage({ text, citations = [], blocked = false, flagged = false, upload = null }) {
  const wrap = document.createElement("div");
  wrap.className = "message assistant" + (blocked ? " blocked" : "");

  const citationsHtml = citations.length
    ? `<div class="badge-row">${citations.map(c => `<span class="citation-chip">${c.id}</span>`).join("")}</div>`
    : "";

  const uploadHtml = uploadBadgeHtml(upload);
  const flagsHtml = (blocked || flagged || uploadHtml)
    ? `<div class="badge-row">
        ${blocked ? `<span class="badge badge-guardrail">Guardrail: request refused</span>` : ""}
        ${flagged && !blocked ? `<span class="badge badge-flag">Flagged: low confidence</span>` : ""}
        ${uploadHtml}
       </div>`
    : "";

  wrap.innerHTML = `
    <div class="avatar assistant-avatar">S</div>
    <div class="bubble">
      <p></p>
      ${flagsHtml}
      ${citationsHtml}
    </div>
  `;
  wrap.querySelector("p").textContent = text;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

// History of {query, score} per answered turn, so the slider can browse
// back through earlier questions instead of only ever showing the latest.
let confidenceHistory = [];

function recordConfidenceTurn(query, score) {
  confidenceHistory.push({ query, score });
  confidenceBlock.hidden = false;
  confidenceSlider.max = String(confidenceHistory.length);
  confidenceSlider.value = String(confidenceHistory.length);
  renderConfidenceAtIndex(confidenceHistory.length - 1);
}

function renderConfidenceAtIndex(idx) {
  const entry = confidenceHistory[idx];
  if (!entry) return;
  const pct = Math.round(entry.score * 100);
  confidenceFill.style.width = pct + "%";
  confidenceValue.textContent = pct + "%";
  const color = entry.score >= 0.7 ? "var(--teal)" : entry.score >= 0.4 ? "var(--amber)" : "var(--red)";
  confidenceFill.style.background = color;
  confidenceValue.style.color = color;
  confidenceTurnLabel.textContent = `Q${idx + 1} of ${confidenceHistory.length}`;
  confidenceQueryLabel.textContent = entry.query;
  confidenceQueryLabel.title = entry.query;
}

confidenceSlider.addEventListener("input", () => {
  renderConfidenceAtIndex(parseInt(confidenceSlider.value, 10) - 1);
});

function updateSourcesPanel(chunks) {
  if (!chunks.length) {
    sourcesList.innerHTML = `<p class="sources-empty">No matching sources survived retrieval + re-ranking for this query.</p>`;
    return;
  }
  sourcesList.innerHTML = chunks.map(c => `
    <div class="source-card">
      <div class="source-card-head">
        <span class="source-tag ${c.tagClass}">${c.tag}</span>
        <span class="source-score">score ${c.score.toFixed(2)}</span>
      </div>
      <h3>${c.title}</h3>
      <p>${c.text}</p>
    </div>
  `).join("");
}

// --- Guardrail + retrieval simulation --------------------------------------
function getActiveSourceTypes() {
  return Array.from(sourceToggles).filter(t => t.checked).map(t => t.value);
}

function isExploitRequest(query) {
  const q = query.toLowerCase();
  return EXPLOIT_KEYWORDS.some(k => q.includes(k));
}

function retrieveChunks(query, activeSources) {
  const q = query.toLowerCase();
  const scored = MOCK_KB
    .filter(item => activeSources.includes(item.tag))
    .map(item => {
      const hits = item.keywords.reduce((n, kw) => n + (q.includes(kw) ? 1 : 0), 0);
      const score = hits > 0 ? 0.6 + Math.min(hits * 0.12, 0.38) : 0.15 + Math.random() * 0.2;
      return { ...item, score };
    })
    .sort((a, b) => b.score - a.score);

  const matched = scored.filter(s => s.score >= 0.6);
  const results = (matched.length ? matched : scored).slice(0, 3);

  if (attachedFile) {
    results.unshift(chunkFromAttachedFile(query));
  }
  return results;
}

function chunkFromAttachedFile(query) {
  const q = query.toLowerCase();
  let text = `Uploaded for this session — content is parsed and chunked server-side by the preprocessing node; not previewable in-browser for this file type.`;
  let score = 0.8;
  if (attachedFile.textContent) {
    const words = attachedFile.textContent.trim().split(/\s+/).slice(0, 40).join(" ");
    text = words + (attachedFile.textContent.split(/\s+/).length > 40 ? "…" : "");
    const hits = q.split(/\s+/).filter(w => w.length > 3 && attachedFile.textContent.toLowerCase().includes(w)).length;
    score = Math.min(0.75 + hits * 0.05, 0.98);
  }
  return {
    tag: "Uploaded", tagClass: "tag-upload", id: attachedFile.name,
    title: `Session upload — ${attachedFile.name}`,
    text, score
  };
}

function composeAnswer(query, chunks) {
  if (!chunks.length) {
    return { text: "I couldn't find any supporting documents for that in the current index. Try enabling more data sources or rephrasing the query.", confidence: 0.2 };
  }
  const lead = chunks[0];
  const supportCount = chunks.filter(c => c.score >= 0.6).length;
  const confidence = supportCount === 0 ? 0.35 : Math.min(0.55 + supportCount * 0.15, 0.95);
  const text = `Based on ${chunks.length} retrieved document${chunks.length > 1 ? "s" : ""}, ${lead.title} indicates: ${lead.text}` +
    (chunks[1] ? ` This is corroborated by ${chunks[1].id}.` : "");
  return { text, confidence };
}

// --- Pipeline orchestration -------------------------------------------------
async function runMockPipeline(query) {
  resetPipeline();
  const activeSources = getActiveSourceTypes();

  await runStageAnimation("ingest", "Reading configured data sources…", 250);
  await runStageAnimation("chunk", "Normalizing & chunking (cached index)…", 250);
  await runStageAnimation("index", "Loading hybrid vector + keyword index…", 300);
  await runStageAnimation("retrieve", "Hybrid search + cross-encoder re-ranking…", 550);

  const chunks = retrieveChunks(query, activeSources);
  updateSourcesPanel(chunks);

  markStage("guardrail", "active");
  setStageLabel("Guardrails: screening query intent…");
  await sleep(350);

  if (isExploitRequest(query)) {
    markStage("guardrail", "blocked");
    markStage("generate", "blocked");
    setStageLabel("Blocked by guardrails — refusing to answer");
    return {
      text: "I can't help generate exploit code, malware, or step-by-step attack instructions. I can instead explain the underlying vulnerability, its impact, and defensive mitigations if you'd like.",
      citations: [],
      confidence: null,
      blocked: true
    };
  }
  markStage("guardrail", "done");

  await runStageAnimation("generate", "Generating grounded answer from citations…", 500);

  const { text, confidence } = composeAnswer(query, chunks);

  await runStageAnimation("eval", "Scoring faithfulness against golden set…", 250);
  await runStageAnimation("deploy", "Logging query + retrieval trace…", 200);

  setStageLabel("Idle — awaiting query");

  return {
    text,
    citations: chunks.map(c => ({ id: c.id })),
    confidence,
    blocked: false,
    flagged: confidence < 0.5
  };
}

async function callBackend(query) {
  const activeSources = getActiveSourceTypes();

  if (attachedFile) {
    const form = new FormData();
    form.append("query", query);
    form.append("sources", JSON.stringify(activeSources));
    form.append("responseLength", String(responseLength));
    form.append("file", attachedFile.file, attachedFile.name);
    const res = await fetch(API_ENDPOINT, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Backend error: ${res.status}`);
    return res.json();
  }

  const res = await fetch(API_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, sources: activeSources, responseLength })
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return res.json();
}

// --- Send flow --------------------------------------------------------------
async function handleSend() {
  const query = queryInput.value.trim();
  if (!query || isBusy) return;

  isBusy = true;
  sendBtn.disabled = true;
  queryInput.disabled = true;
  const showFileChip = attachedFile && !attachedFile.announced;
  appendUserMessage(query, showFileChip ? attachedFile : null);
  if (attachedFile) attachedFile.announced = true;
  queryInput.value = "";
  autoResize();
  appendTypingIndicator();

  try {
    const result = USE_MOCK_PIPELINE ? await runMockPipeline(query) : await callBackend(query);
    removeTypingIndicator();
    appendAssistantMessage(result);
    if (!result.blocked && result.confidence !== null && result.confidence !== undefined) {
      recordConfidenceTurn(query, result.confidence);
    }
  } catch (err) {
    removeTypingIndicator();
    appendAssistantMessage({
      text: `Something went wrong reaching the backend (${err.message}). Is the FastAPI service running at ${API_ENDPOINT}?`,
      blocked: false
    });
    connectionStatus.innerHTML = `<span class="pulse" style="background:var(--red)"></span> Backend: unreachable`;
  } finally {
    isBusy = false;
    sendBtn.disabled = false;
    queryInput.disabled = false;
    queryInput.focus();
  }
}

function autoResize() {
  queryInput.style.height = "auto";
  queryInput.style.height = Math.min(queryInput.scrollHeight, 140) + "px";
}

// --- File attach flow -----------------------------------------------------
function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showAttachedChip() {
  attachedFileName.textContent = attachedFile.name;
  attachedFileSize.textContent = formatFileSize(attachedFile.size);
  attachedChip.hidden = false;
}

function clearAttachedFile() {
  attachedFile = null;
  fileInput.value = "";
  attachedChip.hidden = true;
}

async function handleFileSelected(file) {
  if (!file) return;
  if (file.size > MAX_UPLOAD_BYTES) {
    appendAssistantMessage({ text: `"${file.name}" is ${formatFileSize(file.size)}, which is over the 20 MB session-upload limit.` });
    fileInput.value = "";
    return;
  }

  const ext = "." + file.name.split(".").pop().toLowerCase();
  let textContent = null;
  if (READABLE_TEXT_EXT.includes(ext)) {
    try {
      textContent = await file.text();
    } catch {
      textContent = null;
    }
  }

  attachedFile = { file, name: file.name, size: file.size, textContent, announced: false };
  showAttachedChip();
}

attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => handleFileSelected(e.target.files[0]));
removeFileBtn.addEventListener("click", clearAttachedFile);

// --- Event wiring -------------------------------------------------------
sendBtn.addEventListener("click", handleSend);
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});
queryInput.addEventListener("input", autoResize);

newChatBtn.addEventListener("click", () => {
  messagesEl.innerHTML = `
    <div class="message assistant">
      <div class="avatar assistant-avatar">S</div>
      <div class="bubble"><p>New session started. Ask me about a CVE, an ATT&CK technique, an ICS-CERT advisory, or an internal SOP.</p></div>
    </div>
  `;
  sourcesList.innerHTML = `<p class="sources-empty">No sources retrieved yet. Ask a question to see the hybrid search + re-rank results here.</p>`;
  confidenceBlock.hidden = true;
  confidenceHistory = [];
  confidenceSlider.max = "1";
  confidenceSlider.value = "1";
  clearAttachedFile();
  resetPipeline();
  setStageLabel("Idle — awaiting query");
});

// Mobile panel toggles
const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
const toggleSourcesBtn = document.getElementById("toggleSourcesBtn");
const closeSourcesBtn = document.getElementById("closeSourcesBtn");

toggleSidebarBtn?.addEventListener("click", () => sidebar.classList.toggle("open"));
toggleSourcesBtn?.addEventListener("click", () => sourcesPanel.classList.toggle("open"));
closeSourcesBtn?.addEventListener("click", () => sourcesPanel.classList.remove("open"));

if (USE_MOCK_PIPELINE) {
  connectionStatus.innerHTML = `<span class="pulse"></span> Backend: mock mode`;
}
