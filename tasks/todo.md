# Lead-scoring agent progress

- [x] Analyze recruitment brief and architecture tradeoffs.
- [x] Draft the four-part Spec Kit and incorporate the supplied reviewer findings.
- [x] User review of revised plan. (Approved 2026-11-07.)
- [ ] Implement and validate the service using `specs/lead-scoring-v1/tasks.md`. (Implemented and verified locally with mocks. The real extraction eval is still pending and needs an API key plus the original transcripts.)
- [ ] Deploy, verify, document, and prepare submission.

## Review

2026-11-07: Planning artifacts created. Review corrections cover product-fit eligibility, conservative volume ranges, unresolved license conflicts, traceable evidence, and extraction-level expectations. Static checks passed: all five planning documents exist and 11 policy arithmetic scenarios agree with the specification. No Python application files exist. Model accuracy, API compatibility, endpoint availability, deadlines, and deployed latency require implementation/runtime verification. Awaiting user review of the revised Spec Kit.

2026-11-07 (build, local only): The user approved the Spec Kit.

**What was built:** a FastAPI app under `app/` using Python 3.13.3 in a project `.venv`. It is split into config, models, errors, extraction_schema, extraction, evidence, scoring, rationale, and main. Supporting files are `vercel.json` (maxDuration 30 for `app/main.py`), pinned `requirements*.txt`, `.gitignore`, `.env.example`, `.python-version`, `pytest.ini`, `README.md`, and tests under `tests/`.

**Test results:** `.venv/Scripts/python -m pytest -q` gave 201 passed and 4 skipped. The skips are the real-provider eval in `tests/test_extraction_eval.py`, because `OPENAI_API_KEY` was not set. Coverage:
- Acceptance outputs 85/20/50/70 through `/score`, using mocked extractions.
- Product, personal, and license caps across all 100 product × purpose × license combinations.
- Volume cases and multi-month arithmetic.
- Tier boundaries.
- Evidence rejections, with the specific reason asserted.
- 422 and 413 handling.
- Provider error mapping: refusal, incomplete, rate limit, 5xx, connection, SDK timeout, auth, 4xx, and unexpected.
- Cancellation on both the provider timeout and the handler deadline.
- Injection isolation: developer and user roles only, with no echo.
- Logs contain no transcript or key.

**Mutation check:** I temporarily changed `>= 2` to `> 2` FCL, which produced 116 failures. Dropping `conflicting` from the license cap produced 5 failures. Both changes were restored.

**Implementation choices where the spec is silent:**
1. Provider auth/permission errors return 500 `configuration_error`. Other provider 4xx return 502. Provider 5xx and connection errors return 503.
2. A conflicting import history earns 0 credibility points, even if the business identity is known.
3. A weekly recurrence is treated as `interval_months=0.25`, which is conservative: 4 per month.
4. `named_brand` requires a listed brand token in the cited quotes; otherwise the request returns 502.
5. A conflicting purpose applies no cap. Only confirmed personal use caps the score.
6. Empty message text returns 422. Extra request fields such as `country` are ignored.
7. The 413 limit counts the sum of message `text` lengths.

**Unverified:**
- A real model call and the structured-output compatibility of `gpt-5.4-mini-2026-03-17` with `reasoning.effort=none`.
- Extraction accuracy.
- Whether Vercel detects `app/main.py` with `app.*` package imports.
- Public access, cold-start latency, and latency against 30 s.
- Cancellation on Vercel.
- Repository access.

**Fixture note:** resolved 2026-11-08 — `tests/fixtures.py` now uses the brief's verbatim transcripts.

2026-11-08: User reviewed the seven implementation decisions and kept all of them as built; they are recorded in `specs/lead-scoring-v1/spec.md` under "Approved implementation decisions".

2026-11-08: Read the take-home brief (`northern-coast-takehome.zip`, test-1-build). Replaced placeholder fixtures with its verbatim samples; mocked suite still passes (201 passed, 4 skipped). Spec now records the submission layout (`test-1-build/submission/` with README.md and DEPLOY.md), the three unseen "possibly trickier" grading payloads, and notes on S001's volume clarification and L001's license/history reading. Tests 2 (research) and 3 (RFC critique) are separate deliverables outside this project.

2026-11-08: Moved the project from `ideas 2/lead-scoring-agent` into `northern-coast-ai-takehome/test-1-build/submission/` (unzipped next to the original zip), started a new git repo on branch `test-1`, rebuilt `.venv`, and re-ran the suite: 201 passed, 4 skipped. Added a `DEPLOY.md` stub.
