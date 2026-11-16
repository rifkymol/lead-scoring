# Implementation plan

Status: approved by the user 2026-11-07; implementation in progress.

## Architecture

Use Python 3.13, FastAPI, Pydantic, the OpenAI Python SDK, and pytest. Deploy one FastAPI application on Vercel. Keep request handling, extraction, evidence validation, and scoring as small separate modules; avoid a general agent framework.

Flow: request validation -> one structured extraction call -> evidence and consistency validation -> deterministic monthly normalization, scoring and caps -> deterministic rationale -> response-model validation.

Use `gpt-5.4-mini-2026-03-17` with reasoning effort `none`, configurable through `OPENAI_MODEL`. Keep `OPENAI_API_KEY` in local/server environment variables and out of Git. Confirm API access and a structured response before building out the full extraction path.

Vercel reference: https://vercel.com/docs/frameworks/backend/fastapi
Model reference: https://developers.openai.com/api/docs/models/gpt-5.4-mini
Structured output reference: https://developers.openai.com/api/docs/guides/structured-outputs

## Extraction boundary

Pass the original ordered transcript as serialized data under fixed developer instructions, preserving speaker attribution. Do not map transcript `agent` messages into privileged API messages. Extract only the facts defined in the spec, with evidence and uncertainty states. Use a strict schema with nullable unknown quantities and constrained enums.

Represent volume as lower/upper FCL quantities plus an explicitly supported recurrence interval in months. Python computes the monthly lower bound; one-off or unspecified recurrence yields zero points. License states are held, pending, absent, unknown, and conflicting. Reject impossible intervals, negative quantities, reversed bounds, or contradictory status/evidence combinations with 502.

Evidence validation is an integrity check, not an automated proof of semantic entailment. Keep extraction fixtures that assert specific statuses, ranges, and supporting message indexes independently of final score assertions.

## Reliability and deployment

Use the async provider client. Disable SDK retries; bound the provider call to 22 seconds and the handler work to 25 seconds. Configure the resolved Python entrypoint's Vercel function duration to 30 seconds. Verify that cancellation stops the provider operation and returns the specified JSON error before the platform timeout.

Log request ID, duration, model identifier, and outcome without transcripts or secrets. Preserve provider errors as operational errors, not lead decisions. Pin resolved dependency versions once compatibility is checked.

Deploy `/health` early to establish Python entrypoint detection and public accessibility. After implementation, redeploy and exercise `/score` from an unauthenticated client. Submit the full scoring URL and an accessible repository URL.

## Verification and time budget

Use mocked extractions for exhaustive rule tests; mocked provider outcomes for error/cancellation tests; and real provider calls for extraction evaluations. Assert exact facts and outputs on labeled fixtures, never exact wording of model-generated text. Measure real public endpoint latency separately from local/mock tests.

Target implementation schedule: 0-15 minutes review/setup; 15-30 scaffold and first deployment; 30-65 extraction/scoring; 65-90 tests; 90-110 deployed verification; 110-120 documentation/submission. Record actual time and any deviation honestly.

## Development review roles

The installed `llm-architect` and `architect-reviewer` are optional read-only development reviewers. Inputs: brief, Spec Kit, and later the relevant implementation/tests. Outputs: prioritized evidence-backed findings and residual risks returned to the main agent. They may read source and documentation but receive no authority to edit, deploy, or access secrets. They need only current review context, not persistent application memory. If evidence is unavailable, report the gap. The main agent owns spec updates and implementation; evaluate reviews by concrete defects and verifiable closure. No reviewers run inside the submitted endpoint.

Current evidence: user-supplied read-only review findings informed this revision. No application, model, or deployment checks have run yet.
