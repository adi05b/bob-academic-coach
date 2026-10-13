"""RSI loop: generate -> lint -> evaluate (train personas) -> score -> rewrite the generator prompt.
The artifact that improves is the PROMPT. Held-out test personas never feed back into it."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

from .lint import lint_message
from .llm import complete
from .outreach_agent import generate
from .persona_evaluator import evaluate
from .schemas import Candidate, Evaluation, Iteration, Job, Lint, Message, Persona, Run

ROOT = Path(__file__).resolve().parent.parent
PROMPT_V0 = ROOT / "data" / "prompts" / "generator_v0.md"
RUNS_DIR = Path(__file__).resolve().parent / "runs"
LINT_RULE = "- Never mention"  # prefix of lint rules; they are carried forward even if the optimizer drops them

OPTIMIZER_SYSTEM = """You improve the system prompt of an outreach-message generator.
You get the current prompt, the message it produced, and critiques from the people who received it.
Rewrite the prompt so the next message addresses the critiques. Keep every hard rule (length, citations,
JSON output, never claim anything not in the candidate's lines). Add concrete, checkable instructions.
Return ONLY the full new prompt, no commentary."""


def score(evals: list[Evaluation], lint: Lint) -> float:
    if not lint.passed or not evals:
        return 0.0
    return round(0.5 * mean(e.outcome_reward for e in evals) + 0.5 * mean(e.quality_score for e in evals), 3)


def optimize(prompt: str, message: Message, evals: list[Evaluation], lint: Lint) -> str:
    feedback = "\n".join(f"- {e.persona_id}: {e.outcome}, quality {e.quality_score:.1f}. {e.critique}" for e in evals)
    user = f"CURRENT PROMPT:\n{prompt}\n\nMESSAGE IT PRODUCED:\n{message.text}\n\nRECIPIENT FEEDBACK:\n{feedback}"
    new = complete(OPTIMIZER_SYSTEM, user, "optimize").strip() or prompt
    kept = [l for l in prompt.splitlines() if l.startswith(LINT_RULE) and l not in new]
    if not lint.passed:
        kept.append(f"{LINT_RULE} {', '.join(lint.offending)}: not in the candidate's resume lines.")
    return "\n".join([new, *kept])


def _evaluate_all(personas: list[Persona], message: Message, job: Job, candidate: Candidate) -> list[Evaluation]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda p: evaluate(p, message, job, candidate), personas))


def run_rsi(candidate: Candidate, job: Job, personas: list[Persona], n: int = 4) -> Run:
    train = [p for p in personas if p.split == "train"]
    test = [p for p in personas if p.split == "test"]
    contact = next((p for p in personas if p.id == job.contact_persona_id), train[0])
    allow = f"{contact.name} {contact.company} {job.company} {job.title}"  # names the message may use

    prompt = PROMPT_V0.read_text()
    iterations: list[Iteration] = []
    for i in range(1, n + 1):
        message = generate(prompt, candidate, job, contact)
        lint = lint_message(message.text, candidate, allow)
        evals = _evaluate_all(train, message, job, candidate)
        iterations.append(Iteration(n=i, prompt=prompt, message=message, lint=lint, evals=evals, score=score(evals, lint)))
        if i < n:
            prompt = optimize(prompt, message, evals, lint)

    best = max(iterations, key=lambda it: it.score)
    run = Run(
        id=uuid.uuid4().hex[:12],
        candidate_id=candidate.id,
        job_id=job.id,
        train_persona_ids=[p.id for p in train],
        test_persona_ids=[p.id for p in test],
        iterations=iterations,
        best_n=best.n,
        baseline_test=_evaluate_all(test, iterations[0].message, job, candidate),
        optimized_test=_evaluate_all(test, best.message, job, candidate),
    )
    RUNS_DIR.mkdir(exist_ok=True)
    (RUNS_DIR / f"{run.id}.json").write_text(run.model_dump_json(indent=2))
    return run
