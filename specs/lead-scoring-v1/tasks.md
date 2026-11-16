# Tasks

## Planning gate

- [x] Read the brief and workspace guidance; select Python based on the user's preference.
- [x] Draft the constitution, specification, technical plan, and implementation checklist.
- [x] Incorporate product-fit, volume-range, license-conflict, evidence, and extraction-evaluation review findings.
- [x] Obtain user review of this revised Spec Kit before application implementation. (Approved by the user 2026-11-07.)

## Build and deploy

- [ ] Confirm model API access, Vercel access, and repository destination; keep credentials out of source. (Credentials are kept out of source: `.env` is gitignored and `.env.example` holds placeholders only. API, Vercel and repository access are still unconfirmed because no key was set on 2026-11-07.)
- [x] Scaffold minimal FastAPI request/response models and `/health`; pin compatible runtime dependencies. (Python 3.13.3 local `.venv`; fastapi 0.162.1, openai 3.46.0, pydantic 2.14.3; `vercel.json` sets `app/main.py` maxDuration 30.)
- [ ] Deploy `/health` and verify unauthenticated public access.
- [x] Implement the single structured extraction call and typed evidence/uncertainty states. (Verified with a mocked provider only; no real call has been made yet.)
- [x] Implement evidence checks, monthly lower-bound normalization, deterministic scoring/caps, and rationale templates.
- [x] Implement JSON errors, transcript limit, SDK retry disabling, deadlines/cancellation, and minimal logs. (Cancellation verified locally against a fake provider; not yet verified on Vercel or a real HTTP call.)

## Required verification

- [ ] Check all four supplied examples against both the spec's extracted facts and exact policy outputs. (Partial: policy outputs 85/20/50/70 pass through `/score` with mocked extractions on the brief's verbatim transcripts. Real extraction of the facts is unverified because no API key is set.)
- [x] Verify unrelated product: other signals total 80, final score 39/Cold/archive; unknown product: total 80, final 79/Warm/nurture.
- [x] Verify recurring volume 0.5-1.5 with full brand/credibility/license evidence gives 75/Warm; 1-2 gives 85/Hot; 2-3 gives 100/Hot.
- [x] Verify zero, sub-1, exact-1, exact-2, one-off, upper-bound-only, missing, and conflicting volume cases; check explicit multi-month recurrence arithmetic.
- [x] Verify unknown license can produce 85/Hot; pending, absent, and conflicting license cannot produce Hot. Use the applicable rubric subtotal and cap, not a shared hardcoded score.
- [ ] Verify both license-conflict evidence entries survive extraction; verify a clear later correction can resolve the conflict. (Partial: Python validation keeps both buyer claims, rejects a one-claim conflict, and accepts a corrected `held`. Model behavior is unverified.)
- [x] Verify agent-only assertions do not establish buyer facts; contextual buyer confirmations retain buyer evidence. (This is the Python evidence guard. Semantic extraction behavior still needs the real eval.)
- [x] Reject fabricated quotes, missing/out-of-range indexes, unsupported roles, reversed ranges, and inconsistent status/evidence without returning a score.
- [x] Verify malformed/oversized requests, injection text, provider refusals/rate limits/errors, missing credentials, and timeout cancellation produce the documented behavior. (Verified with a mocked provider. The injection test covers data isolation and that injected text is never echoed, not how the model actually responds.)
- [x] Verify tier boundaries 39/40/79/80, exact success keys, echoed identifiers, integer scores, and every cap combination.
- [x] Replace placeholder fixtures with the brief's verbatim S001/S002/S003/L001 transcripts; mocked tests pass (201 passed, 4 skipped).
- [ ] Add trickier eval payloads modeled on what graders may send: informal or partly non-English text, prompt injection, mixed or unrelated products, one-off orders, volume or license corrections.
- [ ] Run real extraction evaluations, inspect semantic failures even when the final tier is correct, and record commands/results.
- [ ] Deploy the complete service; POST real samples publicly, check JSON and access, and measure fresh and repeated request latency against 30 seconds.

## Delivery

- [x] Move the project into `test-1-build/submission/` of the unzipped take-home, with its own git repo on branch `test-1` (2026-11-08).
- [ ] Fill in `DEPLOY.md` with the live URL, repo URL and verified deploy steps.

- [x] Write the approximately 200-word README with model/rubric rationale, brief ambiguity decisions, setup/example request, and future work; put longer evidence in a separate document. (Drafted; the example uses a `$URL` placeholder until deployment. Longer evidence is in `tasks/todo.md`.)
- [ ] Check repository visibility/access, exclude secrets, record actual hours, and prepare the endpoint/repository/time submission.
- [ ] Record final verification results and residual risks in the project task review; align the Spec Kit with implemented behavior.
