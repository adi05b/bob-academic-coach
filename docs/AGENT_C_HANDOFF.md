# Agent C handoff: resume, matching, and outreach

Agent C owns `career_coach/`, `requirements-agent-c.txt`, `examples/agent_c/`, and
`tests/test_agent_c.py`. This component is independent of a web framework and needs
no model API key. No A/B/D implementation existed when this work began, so the
interfaces below are a concrete provisional contract for the merge agent. The
fixture is explicitly temporary and fictional; replace it with B's data.

## Run and verify

Use Python 3.10 or newer from the repository root:

```shell
python -m pip install -r requirements-agent-c.txt
python -m career_coach demo
python -m career_coach parse examples/agent_c/sample_resume.txt
python -m career_coach parse path/to/uploaded_resume.pdf
python -m unittest discover -s tests -p "test_agent_c.py" -v
```

Only PDF extraction imports `pypdf`. Text parsing, ranking, generation, and the
JSON adapter use the standard library. The tests exercise PDF extraction and
therefore require the dependency. If Windows' `python` points to an unavailable
Store alias, use an installed interpreter or `py` instead.

The checked-in example has three job postings and two contacts. It is a smoke
test for this component, not B's full dataset or D's held-out evaluation corpus.
`demo` returns the temporary-fixture notice alongside its actual computed results.
No sending, evaluation scores, or optimization results are hardcoded.

## Python interface for A and D

```python
from career_coach import (
    BASELINE_INSTRUCTIONS, coach, generate_message, generate_outreach,
    parse_resume_pdf, parse_resume_text, rank_jobs,
)

# A: uploaded bytes stay in memory; no permanent resume storage is required.
candidate = parse_resume_pdf(upload_bytes, source_name="resume.pdf")
# Or use parse_resume_text(resume_text) for B's synthetic resume fixtures.
matches = rank_jobs(candidate, jobs, "software engineer intern", limit=5)
note = generate_outreach(candidate, matches[0]["job"], contact,
                         BASELINE_INSTRUCTIONS,
                         target_role="software engineer intern")

# A: one call also attaches linked contacts and baseline notes to every match.
result = coach(candidate, jobs, contacts, "software engineer intern", limit=5)

# D: this returns just the message string, using the exact same generator.
message = generate_message(candidate, job, contact, instructions)
```

All results are JSON serializable. Public Python functions raise
`CareerCoachError`, a `ValueError` subclass with `code` and `as_dict()`.
There is no HTTP server in Agent C's component; A can expose these functions from
its own backend. D should pass the candidate/job/contact records and its current
generator instructions on **every invocation**, rather than pass a prior message
to rewrite. Calls are deterministic and do not mutate the supplied records.

## JSON/subprocess interface for a non-Python app

```shell
python -m career_coach request --input request.json
```

`request` also reads a single UTF-8 JSON object from stdin. Stdout contains exactly
one JSON response. The process exits 0 for success and 1 for a validation or input
error. It processes one request per invocation, not JSON Lines. Requests are
limited to 20 MiB. A Node backend can spawn Python, write the request to stdin,
then parse stdout; it should keep Python out of the browser bundle.

The same adapter is available in-process as `handle_request(request)`.

| Operation | Required fields | Optional fields | Result |
| --- | --- | --- | --- |
| `parse_resume` | `resume_text` or `pdf_base64` | `source_name`, PDF `password` | Candidate profile |
| `match_jobs` | `candidate`, `jobs` | `target_role`, `limit` | Recommendation array |
| `generate_outreach` | `candidate`, `job`, `contact` | `instructions`, `target_role` | Outreach record |
| `coach` (default) | `candidate` or a resume; `jobs` | `contacts`, `target_role`, `instructions`, `limit` | Candidate + recommendations + notes |

`pdf_base64` is plain, strict base64 without a data-URL prefix. A request cannot
include both resume input forms, or both a candidate and a resume in `coach`.
An omitted `target_role` falls back to `candidate.target_role` when supplied.

```json
{
  "operation": "generate_outreach",
  "candidate": {
    "name": "Alex Rivera",
    "skills": ["Python", "SQL"],
    "projects": [{"name": "Search Prototype", "bullets": ["Built a Python tool used by 25 students."]}]
  },
  "job": {
    "id": "fictional-job-1",
    "title": "Software Engineer Intern",
    "company": "Fable Systems",
    "required_skills": ["Python", "SQL"]
  },
  "contact": {"id": "fictional-contact-1", "name": "Morgan Ellis", "role": "Engineer"},
  "instructions": {"opening": "evidence_first", "include_metrics": true, "max_words": 80}
}
```

Response envelopes:

```json
{"ok": true, "result": {"message": "...", "claims": [], "word_count": 45}}
```

```json
{"ok": false, "error": {"code": "ocr_required", "message": "No readable text was found. This PDF may be scanned; supply OCR text or a text-based PDF."}}
```

The success envelope above abbreviates the real result fields for documentation.
Useful error codes include `invalid_input`, `invalid_operation`, `invalid_pdf`,
`encrypted_pdf`, `ocr_required`, `empty_resume`, `resume_too_large`,
`unsupported_resume`, `missing_dependency`, `invalid_instructions`,
`word_budget_too_small`, and the CLI-only `request_too_large`.

## Input records for B

### Candidate

Preferred: use the profile returned by `parse_resume_text` or `parse_resume_pdf`.
It has `schema_version`, optional `name` and `email`, `skills`, `education`,
`experience`, `projects`, `facts`, `skill_evidence`, `raw_text`, `source_name`, and
`warnings`. PDF profiles also have `page_count`. Entry arrays contain
`{"text": "original source line", "evidence_id": "fact-..."}` records.

Each fact has `id`, `kind`, `text`, and a source object containing `type: "resume"`,
`name`, one-based `line`, zero-based `start`/`end` character offsets into the
**normalized `raw_text`**, and one-based PDF `page` or null. Fact IDs are stable
hashes of kind/text. Their identity does not establish authenticity by itself.

B can instead supply an explicit structured profile:

- `id`, `name`, and `target_role` are optional strings.
- `skills` is an array of strings; aliases such as ReactJS/Postgres are normalized.
- `education`, `experience`, and `projects` are arrays of strings or objects.
- Objects accept `text` directly. Otherwise education accepts `degree`, `field`,
  `institution`/`school`, and `graduation_year` (string or integer); experience
  accepts `title`/`role`, `company`/`organization`; projects accept `name`/`title`.
- Experience/project objects can add `description` and `bullets`/`highlights`
  arrays. Each supplied statement gets profile provenance via a JSON pointer.

Explicit profiles are treated as candidate-supplied facts, with a warning that
they were not independently verified. If `raw_text` is present, C reconstructs
the evidence from it and does not use modified name/education/experience/skills
or arbitrary `facts` to add claims. To accept a human-reviewed structured profile,
omit `raw_text` explicitly at the integration boundary; do not silently fall back
to unverified profile fields when PDF extraction fails.

### Job

Essential fields: `title`, `company` (string or `{ "name": "..." }`), and preferably
a stable string `id`. `job_id`/`company_name` are accepted aliases. If no ID is
provided, C uses `company:title`, so B should provide IDs to avoid collisions.

Other fields: `description`, `required_skills`, `preferred_skills`, `seniority`,
`location`, and `contact_ids` (string arrays). `skills` is an alias for
`required_skills`, `level` for `seniority`, and `contact_id` for one linked contact.
Unrelated fields survive normalization for the UI. Duplicate job IDs are rejected.

### Contact

Essential for `coach`: string `id` (`contact_id` alias). `name`, `role` (`title` or
`type` alias), and string-array `priorities` improve personalization. A missing
name gives a neutral greeting. A contact can be linked through job `contact_ids`,
or contact `job_id`/`job_ids`. C does not select a stranger from an unrelated
company when a link is missing; it returns warnings and no invented contact.

`communication_preferences` (`preferences` alias) may specify `tone` as
`professional`, `warm`, or `direct`; integer `max_words` from 30 to 250; and boolean
`prefers_metrics`. Other evaluator/persona fields are preserved and ignored by C.
Duplicate contact IDs are rejected. B is responsible for internal job/contact
association consistency.

## Recommendation semantics

Every recommendation contains the normalized `job`, `job_id`, `score` (0-100),
`score_kind: "heuristic_relevance_not_probability"`, `matched_skills`,
`missing_skills`, `matched_preferred_skills`, `components`, `reasons`, and `warnings`.
`coach` additionally attaches `contacts` and one `outreach` record per linked
contact. A can render missing skills and evidence limitations alongside the score.

The score uses required skill coverage (weight 60), preferred skill coverage
(weight 10), and stated-goal/title overlap with a small description contribution
(weight 30). Weights for unavailable inputs are omitted from the denominator.
Senior/staff/principal/lead/director/executive postings receive up to a 15-point
penalty because tenure eligibility is not established. Ties break by job ID.
With no positive input overlap the score is zero. These are ranking heuristics,
not qualification guarantees or simulated response scores. Dates, work
authorization, salary, location preferences, and years of professional experience
are not inferred or used as eligibility filters in this MVP.

## Generator instructions for D

The renderer is local and deterministic (`generator: "deterministic_grounded_v1"`).
It generates a new message from facts on every call. It does not call a hosted
LLM and does not interpret every possible natural-language prompt. D can improve
the shared instructions across its training examples, then invoke the same
callable unchanged on B's held-out examples. D owns feedback, scoring, prompt
search, train/evaluation separation, and optimization traces.

Structured instructions are the most reliable contract:

| Field | Default | Accepted values/effect |
| --- | --- | --- |
| `max_words` | 120 | Integer 30-250; hard cap on the **body**, subject excluded |
| `tone` | `professional` | `professional`, `warm`, `direct` |
| `opening` | `role_first` | `role_first`, `evidence_first` |
| `evidence_count` | 1 | Integer 0-3; requested number of distinct resume/profile quotes |
| `include_skills` | true | Include only documented skills, prioritizing job overlap |
| `skill_limit` | 3 | Integer 1-6 |
| `include_metrics` | false | Prefer already documented impact metrics; never add numbers |
| `personalize_contact` | true | Contact priorities affect evidence ranking; role affects the question |
| `adapt_to_contact` | true | Respect persona word cap and unspecified tone/metric preferences |
| `call_to_action` | `question` | `question`, `conversation`, `consideration` |
| `include_subject` | true | Include a subject or return null |

Omitted options use the defaults. Explicit `tone`/`include_metrics` take precedence
over persona preferences. With adaptation enabled, the stricter persona word cap
always wins. `BASELINE_INSTRUCTIONS` is a complete, explicit dictionary; passing
it intentionally fixes tone and metric choices to their listed defaults.
`GenerationInstructions` instances and JSON-object strings are also accepted.
Unknown structured fields and invalid values fail with `invalid_instructions`.

String prompts support directives such as:

```text
tone=warm; opening=evidence_first; evidence_count=2; include_metrics=true; max_words=80
```

Convenience prose supports warm/friendly, direct/professional, evidence-first,
role-first, two/three examples, metrics/quantified/measurable, no metrics, no
skills, no subject, conversation/question, and `under N words`/`at most N words`.
Key/value directives override convenience prose. Arbitrary prose is inert and
returns an interpretation warning; it never supplies new candidate facts. D
should compare `effective_instructions` to confirm that its revision was applied.

The generator chooses relevant documented entries, quotes them without rewriting
the candidate's achievements, and labels skills as listed in the submitted
resume/profile. Truncated quotes end with a visible ` ...`. Quotes may be omitted
to fit the budget. When the fixed greeting/job/ask/signature itself cannot fit,
generation returns `word_budget_too_small` rather than truncate the question or
claim. If there is no usable candidate evidence, the note expresses interest only
and reports a warning.

Outreach records contain `subject`, `message`, `word_count`, `job_id`, `contact_id`,
`target_role`, `effective_instructions`, `claims`, `used_fact_ids`, `grounding`, and
`warnings`. Each candidate claim has its kind, rendered text, fact ID, original
source text, and source coordinates/JSON pointer. Grounding means supported by
the supplied resume/profile, not independently verified employment or achievement.
No statement of prior relationships, recruiter interest, undocumented employers,
unsupported qualifications, or invented metrics is introduced by the renderer.

## Limitations and merge notes

PDF text extraction and heading/name detection are heuristic. The parser handles
text-based PDFs up to 10 MiB, 20 pages, 200,000 extracted characters, and 20 MiB per
decompressed page content stream. Stream checks require decompression; these limits
are not a sandbox for adversarial PDFs. A should run uploads in a resource-limited
backend worker if exposing the demo beyond trusted use. Image-only PDFs return
`ocr_required`; mixed documents warn about pages without text. No OCR is bundled.
Multi-column layouts can interleave text; A should allow profile review. Skills
are detected from a small vocabulary plus explicit comma/semicolon/pipe-delimited
skill lists. Aspiration/negation detection is conservative, not semantic NLP.

No teammate branch was merged or overwritten. `.gitignore` only excludes Python
bytecode, virtual environments, dependency caches, and temporary output. Agent A
can keep its own dependency manifest; the merge agent can consolidate this
component's one runtime dependency later. There is no RSI implementation in C's
files, no B-sized dataset, and no fabricated evaluation result.
