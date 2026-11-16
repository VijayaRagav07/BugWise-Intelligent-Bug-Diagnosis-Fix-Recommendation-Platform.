# Milestone 1.1 — Research & Technical Understanding

## 1. Software Defect Analysis Workflows
In enterprise software engineering (Bugzilla / Jira), manual defect triage follows a five-stage lifecycle:
1. **Ingestion & Validation:** A developer or QA engineer submits a bug report containing a summary, reproduction steps, environment details, and raw stack traces/logs.
2. **Duplicate Detection:** Triage engineers search historical bug repositories to check whether the failure has already been reported or fixed.
3. **Log & Stack Trace Parsing:** Engineers isolate the failing application frames from verbose framework/runtime boilerplate (e.g., `java.lang.reflect`, `org.apache.catalina`).
4. **Severity & Component Routing:** The defect is assigned a severity (`Blocker` to `Trivial`), priority (`P1`–`P4`), and routed to the responsible module owner.
5. **Root Cause Analysis (RCA) & Remediation:** Developers correlate the failure signature with past commits/resolutions to author a patch.

**Key Bottleneck:** [Certain] Over 30–40% of engineering triage time is lost manually reading unstructured logs and hunting for duplicate issues across disparate bug trackers.

---

## 2. RAG Architecture & Retrieval Pipelines
Standard LLMs lack visibility into project-specific defect histories and hallucinate fixes when given raw, unindexed logs. A **Retrieval-Augmented Generation (RAG)** pipeline solves this in two phases:
* **Offline Indexing Pipeline:** Historical bug reports are cleaned, separated into semantic units (Descriptions, Stack Traces, Resolutions), converted into dense vector embeddings, and stored in a local **FAISS** index alongside structured JSON metadata.
* **Online Retrieval Pipeline:** When a new bug is submitted, its description and extracted stack trace are embedded using the exact same model. FAISS performs fast cosine-similarity search (`IndexFlatIP` on L2-normalized vectors) to retrieve the Top-$K$ historical defects, which are then passed as grounded context to the downstream AI agents.

---

## 3. Semantic Similarity, Embeddings & Vector Search (CPU-Optimized)
* **Embedding Model Choice (`all-MiniLM-L6-v2`):** [Certain] Because our deployment environment runs strictly on CPU without a dedicated GPU, heavy 7B+ embedding models are impractical. `sentence-transformers/all-MiniLM-L6-v2` (~80 MB, 384 dimensions) generates embeddings at >100 chunks/second on CPU while preserving high semantic accuracy for technical text.
* **Similarity Metric (Cosine Similarity via Inner Product):** [Certain] By L2-normalizing all embedding vectors prior to indexing, Euclidean distance rankings align with Cosine Similarity, allowing `faiss.IndexFlatIP` to compute exact similarity scores in milliseconds[cite: 1].
* **Handling Structural Noise:** Raw stack traces contain memory addresses, timestamps, and deep library paths that dilute semantic similarity. Separating stack traces from natural-language descriptions into distinct chunk types prevents boilerplate frames from drowning out symptom descriptions.

---

## 4. Historical Bug Report Structures (Mozilla, Apache, Eclipse)
| Ecosystem | Tracker | Key Raw Fields | Common Data Quality Challenges |
| :--- | :--- | :--- | :--- |
| **Eclipse** | Bugzilla | `bug_id`, `short_desc`, `description`, `component`, `product`, `resolution`, `dup_id` | Automated build-bot comments, long inline Java stack traces, `"WORKSFORME"` / `"INVALID"` noise. |
| **Apache** | Jira | `key`, `summary`, `description`, `components`, `resolution`, `issuelinks`, `comments` | Jira markup tags (`{code}`, `{noformat}`), multi-patch discussion threads. |
| **Mozilla** | Bugzilla | `id`, `summary`, `cf_crash_signature`, `product`, `component`, `resolution` | C++ hex memory dumps, platform-specific crash signatures, missing reproduction steps. |

**Standardization Strategy:** All external datasets are normalized into a unified internal schema (`chunk_id`, `source_dataset`, `original_bug_id`, `chunk_type`, `content`, `component`, `resolution`, `exception_types`) and filtered strictly to verified `FIXED` or `DUPLICATE` records.

---

## 5. Proposed Technology Choices (Milestone 1 Stack)
* **Backend Framework:** **FastAPI** (Python) — async request handling, automatic OpenAPI docs, and strict Pydantic schema validation[cite: 1].
* **Frontend Interface:** **React + Vite** (or lightweight web client) — responsive submission portal for pasting logs and uploading files[cite: 1].
* **Submission Database:** **SQLite** — zero-configuration relational persistence for incoming bug reports and extracted exception metadata[cite: 1].
* **Embedding Engine:** **Sentence-Transformers (`all-MiniLM-L6-v2`)** — fast CPU inference.
* **Vector Store:** **FAISS (`faiss-cpu`)** — local disk-persisted vector index (`bug_chunks.faiss`) paired with JSON metadata (`bug_metadata.json`)[cite: 1].