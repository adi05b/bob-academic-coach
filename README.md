# Career Coach

A self-improving outreach agent that can't learn to lie.

## Team

| Name | GitHub |
|---|---|
| Aditi Bombe | adi05b |
| TBD | yjoechuen |
| TBD | shalondam7-ctrl |

## Summary

Career Coach writes LinkedIn outreach for a new-grad candidate and improves itself by recursive self-improvement (RSI). Here, RSI means one thing: an optimizer rewrites the generator's prompt using feedback from simulated personas (CEOs, recruiters and engineers, each with their own priorities and pet peeves). The prompt is the artifact that improves; the model weights never change. A fabrication linter acts as a hard constraint: any number, tool or proper noun that is not in the candidate's resume zeroes that iteration's score, so the loop cannot learn to win by inventing claims. The optimizer only sees train personas. Results are reported on held-out test personas to show generalization. Every score comes from a simulated reward model (an LLM playing a persona), so the numbers measure generalization to unseen simulated readers, not real recruiter response rates.

## How to run (app)

Live frontend: **https://career-coach-three-theta.vercel.app** (it calls the backend at `NEXT_PUBLIC_API_URL`, default `http://localhost:8000`, so start the backend locally first).

```bash
git clone https://github.com/adi05b/bob-academic-coach.git && cd bob-academic-coach
```

**Backend** (Python 3.11, run from the repo root):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env        # set OPENROUTER_API_KEY for live LLM calls
uvicorn backend.main:app --reload --port 8000
```

**Frontend** (in a second terminal, then open http://localhost:3000):

```bash
cd frontend && npm install && npm run dev
```

**Tests:** run `pytest` from the repo root. It covers the linter, backend API, and Agent B dataset generation.

**Mock mode:** if `OPENROUTER_API_KEY` is empty, the backend uses fixtures from `backend/mock/`. See [docs/DESIGN.md](docs/DESIGN.md) for the loop, contracts, and file ownership.

## Agent B — synthetic world (`data/synthetic/`)

Expanded dataset for multi-agent integration (companies, hiring personas, jobs, grounded profiles):

- **8 companies**, **16 contacts**, **100 jobs**, **9 candidates** (3/3/3 train/val/test)
- Ground-truth **`profile`** per candidate; **`match_labels.jsonl`** for job fit
- Regenerate: `pip install -e ".[dev]"` then `python -m data.generate`

Handoff for Agents C and D: [DATA_CONTRACT.md](DATA_CONTRACT.md). Legacy sample fixtures for the app remain in `data/jobs.json`, `data/personas.json`, `data/resumes.json`.

## Agent D — RSI prototype (`agent_d/`)

Workshop-style `tailor_resume` program evolution (separate from the backend outreach-prompt RSI). Run `python agent_d/run_rsi.py --baseline-only` from the repo root.
