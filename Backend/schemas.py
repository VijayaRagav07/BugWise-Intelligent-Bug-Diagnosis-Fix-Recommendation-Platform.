from pydantic import BaseModel
from typing import List, Optional

class BugSubmissionResponse(BaseModel):
    bug_id: str
    title: str
    description: str
    stack_trace: str
    environment: str
    component: str
    uploaded_files: List[str]
    detected_exceptions: List[str]
    status: str
    created_at: str

class SimilarBugHit(BaseModel):
    chunk_id: str
    original_bug_id: str
    chunk_type: str
    content: str
    product: Optional[str] = "Eclipse"
    component: str
    resolution: str
    duplicate_of: Optional[str] = None
    similarity_score: float