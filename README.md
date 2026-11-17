# Northern Coast lead-scoring API

FastAPI service that scores beverage buyer inquiries and routes them to sales.

Live: `POST https://lead-scoring-eight.vercel.app/score` (health check: `GET /health`). See [DEPLOY.md](DEPLOY.md) for verification results.

## Setup

```bash
py -3.13 -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
cp .env.example .env   # set OPENAI_API_KEY; OPENAI_MODEL is optional
.venv/Scripts/python -m pytest      # mocked tests; real eval runs only with a key
```

```bash
curl -X POST https://lead-scoring-eight.vercel.app/score -H "Content-Type: application/json" \
  -d '{"lead_id":"S001","channel":"email","conversation":[{"role":"lead","text":"We need 2 FCL of Red Bull monthly."}]}'
```

## Design

The service makes one structured extraction call to `gpt-5.4-mini` with reasoning effort `none`. This is a small, fast model chosen to stay within the 30-second limit. Python then checks every cited quote against the transcript and computes the score with a fixed rubric: product fit 20, recurring monthly FCL 35, credibility 30, license 15. After that it applies caps, and finally it writes the reasoning from a template. The model never chooses the score.

Facts the buyer has not stated stay unknown, and contradictory claims stay conflicting. An agent's question or assertion never counts as a buyer fact.

**Ambiguity:** the brief's example routes a Warm lead to KAM. I followed the explicit mapping instead: Hot goes to `kam_handoff`, Warm to `nurture_pool`, Cold to `auto_archive`.

## Future work

- Grow the eval set beyond 18 cases (14 harder ones live in `tests/tricky_cases.py`) and track per-fact accuracy, not just score.
- Expand the brand catalog.
- Verify licenses against registries.

**Time spent:** about 1.5 hours.
