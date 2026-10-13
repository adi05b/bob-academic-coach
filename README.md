# Hey Bob

Hackathon-scale AI career coach (synthetic data + simulated hiring personas).

## Agent B — synthetic world (`data/`)

- **8 companies**, **16 hiring contacts**, **100 jobs**, **9 candidates** (3/3/3 train/val/test)
- Ground-truth **`profile`** per candidate (skills + allowed phrases); resume text is rendered from it
- **Job–candidate fit** in `match_labels.jsonl`; each job links to a **contact persona**

```bash
pip install -e ".[dev]"
python -m data.generate
pytest
```

Integration details: [DATA_CONTRACT.md](DATA_CONTRACT.md)

## Agent D — RSI prototype (`agent_d/`)

Resume-tailoring RSI (workshop-style program evolution). Product RSI for **outreach prompts** should live here and use `contacts.json` — see [AGENT_D.md](AGENT_D.md).

```bash
cp .env.example .env   # add OPENROUTER_API_KEY
python agent_d/run_rsi.py --baseline-only
```

## Branches

Work on `agent-b` / `agent-d-rsi` (etc.) and merge to `main` via PR. Shared contracts live in `DATA_CONTRACT.md`.
