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

## How to run

Live frontend: **LIVE_URL_PLACEHOLDER** (it calls the backend at `NEXT_PUBLIC_API_URL`, default `http://localhost:8000`, so start the backend locally first).

```bash
git clone https://github.com/adi05b/bob-academic-coach.git && cd bob-academic-coach
```

**Backend** (Python 3.11, run from the repo root):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env        # leave OPENROUTER_API_KEY empty for mock mode
uvicorn backend.main:app --reload --port 8000
```

**Frontend** (in a second terminal, then open http://localhost:3000):

```bash
cd frontend && npm install && npm run dev
```

**Tests:** run `pytest` from the repo root. It covers the linter and runs an end-to-end mock run.

**Mock mode:** if `OPENROUTER_API_KEY` is empty, every LLM call returns a fixture from `backend/mock/` and nothing raises. Click **Use sample resume**, pick a job and hit **Run**. Over 4 iterations the score goes 0.00 → 0.40 → 0.63 → 0.87: iteration 1 fabricates "Kafka" and "10x", so the linter zeroes it, and the held-out reward goes 0.07 → 0.80. The fixtures are written for the sample candidate. A different resume in mock mode fails the linter, which is correct behavior. Set the key (and optionally `BOB_MODEL`) in `.env` for live runs. See [docs/DESIGN.md](docs/DESIGN.md) for the loop, contracts, and who owns which file.
