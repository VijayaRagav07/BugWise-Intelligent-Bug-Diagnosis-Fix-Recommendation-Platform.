import re
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from database import get_connection
from schemas import BugSubmissionResponse, SimilarBugHit
from kb.retriever import DefectRetriever

router = APIRouter(prefix="/api/bugs", tags=["Bugs & RAG Retrieval"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".stacktrace"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Load FAISS retriever once when server starts
retriever = DefectRetriever()

def scrub_sensitive_info(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED_IP]', text)
    text = re.sub(r'(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+', r'\1=[REDACTED]', text)
    return text.strip()

def extract_exceptions(text: str) -> List[str]:
    matches = re.findall(r'\b([a-zA-Z0-9_$.]+(?:Exception|Error|Fault))\b', text)
    return sorted(list(set(matches)))

@router.post("/submit", response_model=BugSubmissionResponse, status_code=201)
async def submit_bug_report(
    title: str = Form(...),
    description: str = Form(...),
    stack_trace: str = Form(""),
    environment: str = Form("Unknown"),
    component: str = Form("General"),
    files: Optional[List[UploadFile]] = File(None)
):
    if len(title.strip()) < 5:
        raise HTTPException(status_code=400, detail="Title must be at least 5 characters.")
    if len(description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Description must be at least 10 characters.")

    clean_title = scrub_sensitive_info(title)
    clean_desc = scrub_sensitive_info(description)
    clean_trace = scrub_sensitive_info(stack_trace)

    combined_logs = f"{clean_desc}\n{clean_trace}"
    saved_files: List[str] = []

    if files:
        for upload in files:
            if not upload.filename:
                continue
            ext = Path(upload.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

            raw_bytes = await upload.read()
            if len(raw_bytes) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"File '{upload.filename}' exceeds 5MB.")

            decoded = scrub_sensitive_info(raw_bytes.decode("utf-8", errors="replace"))
            combined_logs += f"\n{decoded}"

            stored_name = f"{uuid.uuid4().hex[:8]}_{Path(upload.filename).name}"
            (UPLOAD_DIR / stored_name).write_text(decoded, encoding="utf-8")
            saved_files.append(stored_name)

    bug_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    exceptions = extract_exceptions(combined_logs)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO bug_submissions (
                bug_id, title, description, stack_trace, environment,
                component, uploaded_files, detected_exceptions, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bug_id, clean_title, clean_desc, clean_trace, environment.strip(),
                component.strip(), json.dumps(saved_files), json.dumps(exceptions),
                "SUBMITTED", created_at
            )
        )
        conn.commit()

    return BugSubmissionResponse(
        bug_id=bug_id,
        title=clean_title,
        description=clean_desc,
        stack_trace=clean_trace,
        environment=environment.strip(),
        component=component.strip(),
        uploaded_files=saved_files,
        detected_exceptions=exceptions,
        status="SUBMITTED",
        created_at=created_at
    )

@router.get("/", response_model=List[BugSubmissionResponse])
def list_bugs():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM bug_submissions ORDER BY created_at DESC").fetchall()
        return [
            BugSubmissionResponse(
                bug_id=r["bug_id"],
                title=r["title"],
                description=r["description"],
                stack_trace=r["stack_trace"] or "",
                environment=r["environment"] or "Unknown",
                component=r["component"] or "General",
                uploaded_files=json.loads(r["uploaded_files"] or "[]"),
                detected_exceptions=json.loads(r["detected_exceptions"] or "[]"),
                status=r["status"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

@router.get("/similar", response_model=List[SimilarBugHit])
def search_similar_historical_bugs(
    q: str = Query(..., min_length=5, description="Bug symptom or stack trace query"),
    top_k: int = Query(5, ge=1, le=20)
):
    return retriever.search(q, top_k=top_k)