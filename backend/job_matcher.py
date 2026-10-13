"""Baseline matcher: keyword/stem overlap between job reqs and candidate lines. No LLM.
TODO: swap in embeddings or an LLM judge, keep the JobMatch output shape."""
import re

from .schemas import Candidate, Job, JobMatch, MatchRow

STOP = {
    "a", "an", "and", "or", "the", "in", "on", "of", "to", "for", "with", "by", "as", "at", "is", "are", "be",
    "our", "your", "you", "we", "it", "its", "into", "from", "that", "this", "like", "such", "similar", "other",
    "related", "field", "experience", "strong", "plus", "bonus", "ability", "familiarity", "understanding",
    "proficiency", "comfortable", "interest", "work", "working", "build", "building", "using", "use", "clear",
}
WEIGHT = {"Covered": 1.0, "Mapped": 0.6, "Thin": 0.3, "Gap": 0.0}


def stems(text: str) -> set[str]:
    # ponytail: 5-char prefix "stemmer" (deploy/deployed/deployment -> deplo). Swap for a real stemmer if it misfires.
    return {w[:5] for w in re.findall(r"[a-z][a-z0-9+#.]*", text.lower()) if w not in STOP and len(w) > 1}


def match_job(candidate: Candidate, job: Job) -> JobMatch:
    lines = [(l.id, stems(l.text)) for l in candidate.lines]
    rows = []
    for req in job.reqs:
        want = stems(req.text)
        hits = sorted(((len(want & s), rid) for rid, s in lines if want & s), reverse=True)
        best = hits[0][0] / len(want) if hits and want else 0.0
        status = "Covered" if best >= 0.5 else "Mapped" if best >= 0.3 else "Thin" if best > 0 else "Gap"
        rows.append(MatchRow(j=req.id, status=status, r=[rid for _, rid in hits[:3]]))
    score = round(100 * sum(WEIGHT[r.status] for r in rows) / max(len(rows), 1))
    return JobMatch(job_id=job.id, score=score, rows=rows)


def match(candidate: Candidate, jobs: list[Job], target_role: str = "") -> list[JobMatch]:
    """Ranked best-first. A job whose title shares a word with target_role ranks above the rest."""
    role = stems(target_role)
    by_id = {j.id: j for j in jobs}
    ranked = [match_job(candidate, j) for j in jobs]
    return sorted(ranked, key=lambda m: (bool(role & stems(by_id[m.job_id].title)), m.score), reverse=True)
