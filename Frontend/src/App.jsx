import { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api/bugs";

export default function App() {
  const [activeTab, setActiveTab] = useState("submit");
  const [bugs, setBugs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState(null);

  const [title, setTitle] = useState("");
  const [component, setComponent] = useState("JDT / Core");
  const [environment, setEnvironment] = useState("Windows 11 | JDK 21");
  const [description, setDescription] = useState("");
  const [stackTrace, setStackTrace] = useState("");
  const [files, setFiles] = useState([]);

  const [searchQuery, setSearchQuery] = useState("");
  const [similarHits, setSimilarHits] = useState([]);
  const [searching, setSearching] = useState(false);

  const loadSubmittedBugs = async () => {
    try {
      const res = await fetch(`${API_BASE}/`);
      if (res.ok) setBugs(await res.json());
    } catch (err) {
      console.error("Backend unreachable:", err);
    }
  };

  useEffect(() => {
    loadSubmittedBugs();
  }, []);

  const runRagSearch = async (overrideQuery) => {
    const queryToRun = (overrideQuery ?? searchQuery).trim();
    if (queryToRun.length < 5) return;

    setSearching(true);
    try {
      const res = await fetch(
        `${API_BASE}/similar?q=${encodeURIComponent(queryToRun)}&top_k=5`
      );
      if (res.ok) setSimilarHits(await res.json());
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  };

  const handleBugSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setBanner(null);

    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("description", description);
      formData.append("stack_trace", stackTrace);
      formData.append("environment", environment);
      formData.append("component", component);
      files.forEach((file) => formData.append("files", file));

      const res = await fetch(`${API_BASE}/submit`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to submit defect report.");

      setBanner({
        type: "success",
        text: `Defect ${data.bug_id} persisted! Auto-detected ${data.detected_exceptions.length} exception signature(s).`,
      });

      setTitle("");
      setDescription("");
      setStackTrace("");
      setFiles([]);
      await loadSubmittedBugs();

      const combinedQuery = `${data.title} ${data.description}`.slice(0, 300);
      setSearchQuery(combinedQuery);
      setActiveTab("search");
      await runRagSearch(combinedQuery);
    } catch (err) {
      setBanner({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="header-inner">
          <h1>Autonomous Defect Intelligence System</h1>
          <p className="subtitle">
            Defect Ingestion Portal (M1.3) &amp; Historical Eclipse FAISS Knowledge Base (M1.4)
          </p>
        </div>
      </header>

      <main className="main-content">
        <nav className="tab-bar">
          <button
            className={activeTab === "submit" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("submit")}
          >
            Submit Defect Report
          </button>
          <button
            className={activeTab === "search" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("search")}
          >
            Historical RAG Search
          </button>
          <button
            className={activeTab === "queue" ? "tab-btn active" : "tab-btn"}
            onClick={() => setActiveTab("queue")}
          >
            Submitted Queue ({bugs.length})
          </button>
        </nav>

        {banner && <div className={`banner ${banner.type}`}>{banner.text}</div>}

        {activeTab === "submit" && (
          <form className="panel" onSubmit={handleBugSubmit}>
            <div className="panel-header">
              <h2>Ingest New Defect Report</h2>
              <p>IP addresses, tokens, and ANSI codes are automatically scrubbed prior to persistence.</p>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>Defect Summary / Title *</span>
                <input
                  type="text"
                  required
                  minLength={5}
                  placeholder="e.g., NullPointerException in org.eclipse.jdt when opening editor"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>

              <label className="field">
                <span>Target Component</span>
                <input
                  type="text"
                  value={component}
                  onChange={(e) => setComponent(e.target.value)}
                />
              </label>
            </div>

            <label className="field">
              <span>Runtime Environment (OS / JDK / Build)</span>
              <input
                type="text"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
              />
            </label>

            <label className="field">
              <span>Observed Behavior &amp; Reproduction Steps *</span>
              <textarea
                rows={4}
                required
                minLength={10}
                placeholder="Describe expected vs. actual behavior..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>

            <label className="field">
              <span>Raw Stack Trace (Optional)</span>
              <textarea
                rows={5}
                className="code-input"
                placeholder="Paste stack trace frames here..."
                value={stackTrace}
                onChange={(e) => setStackTrace(e.target.value)}
              />
            </label>

            <label className="field">
              <span>Attach Diagnostic Logs (.log, .txt, .json, .stacktrace)</span>
              <input
                type="file"
                multiple
                accept=".log,.txt,.json,.stacktrace"
                onChange={(e) => setFiles(Array.from(e.target.files))}
              />
            </label>

            <button type="submit" className="primary-btn" disabled={loading}>
              {loading ? "Validating & Indexing..." : "Submit Report & Query Historical KB"}
            </button>
          </form>
        )}

        {activeTab === "search" && (
          <div className="panel">
            <div className="panel-header">
              <h2>Semantic Historical Defect Retrieval</h2>
              <p>Queries the 5,000-record Eclipse Bugzilla FAISS index via all-MiniLM-L6-v2 embeddings.</p>
            </div>

            <div className="search-row">
              <input
                type="text"
                placeholder="Enter defect symptom or exception (e.g., ConcurrentModificationException in JDT)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runRagSearch()}
              />
              <button
                className="primary-btn"
                onClick={() => runRagSearch()}
                disabled={searching}
              >
                {searching ? "Searching..." : "Retrieve Matches"}
              </button>
            </div>

            <div className="results-stack">
              {similarHits.length === 0 ? (
                <p className="empty-state">
                  Enter a query above to retrieve the Top-5 semantically similar historical defects.
                </p>
              ) : (
                similarHits.map((hit) => (
                  <article key={hit.chunk_id} className="record-card">
                    <div className="record-meta">
                      <span className="bug-tag">{hit.original_bug_id}</span>
                      <span className="gold-pill">
                        Similarity: {(hit.similarity_score * 100).toFixed(1)}%
                      </span>
                      <span className="neutral-pill">{hit.resolution}</span>
                      <span className="neutral-pill">{hit.component}</span>
                    </div>
                    <pre className="record-body">{hit.content}</pre>
                  </article>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === "queue" && (
          <div className="panel">
            <div className="panel-header">
              <h2>Persisted Defect Queue (SQLite)</h2>
              <p>Validated submissions ready for Milestone 2 multi-agent triage.</p>
            </div>

            {bugs.length === 0 ? (
              <p className="empty-state">No defect reports submitted yet.</p>
            ) : (
              <div className="results-stack">
                {bugs.map((bug) => (
                  <article key={bug.bug_id} className="record-card">
                    <div className="record-meta">
                      <span className="bug-tag">{bug.bug_id}</span>
                      <strong>{bug.title}</strong>
                      <span className="neutral-pill">{bug.component}</span>
                      <span className="gold-pill">{bug.status}</span>
                    </div>
                    <p className="record-desc">{bug.description}</p>
                    {bug.detected_exceptions.length > 0 && (
                      <div className="exception-row">
                        <span>Detected Exceptions: </span>
                        {bug.detected_exceptions.map((ex) => (
                          <code key={ex} className="ex-chip">{ex}</code>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}