from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes.bugs import router as bugs_router

init_db()

app = FastAPI(
    title="Autonomous Defect Intelligence System - Milestone 1",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bugs_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "milestone": "M1"}