"""HTTP surface. Run from the repo root: uvicorn backend.main:app --reload --port 8000"""
import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import llm
from .job_matcher import match
from .resume_parser import parse_pdf, parse_text
from .rsi_optimizer import RUNS_DIR, run_rsi
from .schemas import Candidate, Job, JobMatch, Persona, Run

DATA = Path(__file__).resolve().parent.parent / "data"
JOBS = [Job(**j) for j in json.loads((DATA / "jobs.json").read_text())]
PERSONAS = [Persona(**p) for p in json.loads((DATA / "personas.json").read_text())]
RESUMES = [Candidate(**c) for c in json.loads((DATA / "resumes.json").read_text())]

app = FastAPI(title="Career Coach")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class MatchBody(BaseModel):
    candidate: Candidate
    target_role: str = ""


class RunBody(BaseModel):
    candidate: Candidate
    job_id: str
    n: int = Field(4, ge=1, le=8)


@app.get("/health")
def health():
    return {"mock": llm.MOCK, "model": llm.MODEL}


@app.post("/resume", response_model=Candidate)
async def resume(request: Request):
    """multipart/form-data with `file` (PDF or .txt), or JSON {"text": "..."}."""
    if request.headers.get("content-type", "").startswith("multipart/"):
        upload = (await request.form()).get("file")
        if upload is None or isinstance(upload, str):
            raise HTTPException(400, "send the resume as form field `file`")
        data = await upload.read()
        try:
            cand = parse_pdf(data) if data[:5] == b"%PDF-" else parse_text(data.decode("utf-8", "ignore"))
        except Exception as e:
            raise HTTPException(400, f"could not read file: {e}")
    else:
        body = await request.json()
        cand = parse_text(str(body.get("text", "")) if isinstance(body, dict) else "")
    if not cand.lines:
        raise HTTPException(400, "no resume lines found")
    return cand


@app.get("/jobs", response_model=list[Job])
def jobs():
    return JOBS


@app.get("/personas", response_model=list[Persona])
def personas():
    return PERSONAS


@app.get("/resumes", response_model=list[Candidate])
def resumes():
    """Synthetic sample candidates. Mock fixtures are written for the first one."""
    return RESUMES


@app.post("/match", response_model=list[JobMatch])
def match_jobs(body: MatchBody):
    return match(body.candidate, JOBS, body.target_role)


@app.post("/run", response_model=Run)
def run(body: RunBody):
    job = next((j for j in JOBS if j.id == body.job_id), None)
    if job is None:
        raise HTTPException(404, f"unknown job_id {body.job_id}")
    return run_rsi(body.candidate, job, PERSONAS, body.n)


@app.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str):
    path = RUNS_DIR / f"{run_id}.json"
    if not re.fullmatch(r"[a-f0-9]{1,32}", run_id) or not path.exists():
        raise HTTPException(404, "run not found")
    return Run.model_validate_json(path.read_text())
