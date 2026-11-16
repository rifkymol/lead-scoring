# Lead-scoring API specification

Status: approved by the user 2026-11-07; implementation in progress.
Updated: 2026-11-08 (Asia/Jakarta).
Source: Northern Coast take-home brief at `../BRIEF.md` (`test-1-build/BRIEF.md`) and user-supplied architecture review findings.

## Goal and contract

Help Northern Coast's sales team route beverage buyer inquiries consistently. Deliver a public Vercel scoring URL, accessible code repository, approximately 200-word README (model, why, what to do with more time), and approximate hours spent. The take-home asks for the work in `test-1-build/submission/` (code, `README.md`, and `DEPLOY.md` or the live URL), zipped with the other tests' submissions.

The graders POST three different payloads of similar shape, "possibly trickier" than the samples, and judge: the URL returns valid JSON for all three, code quality and model choice, the README's reasoning, and failure handling for malformed input and LLM failures. Leads come from wholesalers in 60+ countries, so transcripts may be informal, partly non-English, or adversarial.

`POST /score` accepts the brief's `lead_id`, `channel`, and nonempty `conversation` array of `{role: "lead" | "agent", text: string}`. Return exactly `lead_id`, integer `score` (0-100), `tier`, `routing`, and a one- or two-sentence `reasoning`. Echo the input identifier in code. Channel and country do not change scoring weights.

`GET /health` returns service status without calling the model. Successful scoring and application-controlled errors must complete within the 30-second submission requirement; measure deployed behavior before claiming compliance.

The explicit business mapping takes precedence over the brief's inconsistent Warm/KAM example: Hot means KAM, Warm means nurture, Cold means archive. Document this assumption in the README. The sample score 78 is illustrative, not a required exact value.

## Extraction and evidence

Extract product fit, explicit recurring FCL quantity/range and recurrence, business credibility, license status, and personal-use intent. Preserve `unknown` and `conflicting` states rather than filling gaps with guesses.

Every known fact carries evidence entries with a zero-based `message_index` and exact `quote`. Each entry must reference an existing original message and contain a nonempty substring of that message. At least one supporting entry per known buyer fact must reference a `lead` message. An explicit buyer confirmation such as "yes" may additionally reference the immediately preceding agent question for context. An agent question or assertion without buyer confirmation cannot establish a fact.

Unknown facts have no affirmative evidence and earn no points. Conflicting facts cite both incompatible buyer claims. A clear later correction or dated status update resolves the older claim; merely appearing later does not erase an unresolved contradiction. A known fact with missing or invalid evidence invalidates the extraction and returns 502; do not silently turn it into a Cold lead.

Validate indexes, roles, quotations, enums, numerical bounds, and cross-field consistency in Python. These structural checks cannot prove that quotes support an interpretation; labeled extraction tests cover that separate semantic risk.

## Scoring policy

Calculate the subtotal, apply every applicable cap using the lowest cap, then derive tier and routing from the final integer score.

| Factor | Points |
|---|---|
| Product: Coca-Cola, Monster, or Red Bull / other beverage / unrelated, unknown, or conflicting | 20 / 10 / 0 |
| Recurring monthly FCL: >=2 / >=1 and <2 / >0 and <1 / zero, unknown, conflicting, or nonrecurring | 35 / 20 / 10 / 0 |
| Credibility: >=3 years importing plus distribution network / importing history / identifiable B2B buyer without established history / unknown or conflicting | 30 / 15 / 5 / 0 |
| License: explicitly held / pending / explicitly absent, unknown, or conflicting | 15 / 5 / 0 |

The named-brand list is an initial policy assumption from the brief, not a complete verified company catalog. Other beverages receive partial fit; confirmed unrelated means the inquiry requests only products outside beverage supply. A mixed inquiry with an explicitly requested beverage is evaluated for its beverage demand.

Caps:

- Confirmed unrelated-product inquiry or personal-use purchase: maximum 39.
- Unknown or conflicting product fit: maximum 79.
- Pending, explicitly absent, or conflicting license: maximum 79.
- Unknown licensing earns zero license points but does not itself cap the score, because the brief's Hot sample does not confirm a license. Explain that uncertainty in the rationale.

Use the lower bound of an explicit recurring volume range. Derive monthly volume in Python from stated FCL quantities and stated recurrence; do not infer pallet/can conversions or treat one-off orders as recurring. "Up to 3 FCL/month" has no positive committed lower bound and earns zero volume points. Vague or unresolved conflicting volume also earns zero.

| Final score | Tier | Routing |
|---|---|---|
| 80-100 | Hot | kam_handoff |
| 40-79 | Warm | nurture_pool |
| 0-39 | Cold | auto_archive |

Generate the rationale in Python from validated facts and applied caps. Mention a decisive blocker or material uncertainty; describe held licenses as reported, not verified. Do not make a second model call.

## Acceptance examples and failures

| Supplied example | Required extracted facts | Policy result |
|---|---|---|
| S001 UAE | Named brand; 2-3 recurring FCL/month; 8 years importing; retail network; license unknown | 85, Hot, kam_handoff |
| S002 office party | Named brand; personal use; recurring FCL unknown; history/license unknown | 20, Cold, auto_archive |
| S003 Ghana | Named brand; 1 recurring FCL/month; new B2B entrant; license pending | 50, Warm, nurture_pool |
| L001 original contract example | Named brand; 1 recurring FCL/month; importing history; reported license held | 70, Warm, nurture_pool |

Return JSON errors for invalid requests (422), input above the documented 20,000-character transcript limit (413), unusable/refused/invalid-evidence extraction (502), unavailable or rate-limited provider (503), timeout (504), and missing server credentials or unexpected application failure (500). Error bodies use `{error: {code, message}, request_id}` and contain no score. These are implementation choices where the brief is silent.

Before submission, verify public access without a Vercel login, repository accessibility, exact success fields, a real model response, and end-to-end latency. Runtime accuracy, model access, cold-start latency, and cancellation behavior are currently unverified.

## Sample transcript notes

Checked against the brief's verbatim samples on 2026-11-08:

- S001 first says "3 FCL/month Red Bull", then answers the agent's Red Bull-specific question with "2-3 FCL/month sustained". Treat the later product-specific answer as a clarification, not a conflict; the lower bound 2 earns 35 points either way.
- L001 "licensed 4 years" reports a held license (confirmed by "Yes" to the agent's license question). "Currently import 2 brands" establishes importing history without stated import years or a distribution network, so credibility is 15.

## Approved implementation decisions

Approved by the user on 2026-11-08 where the brief and earlier spec were silent:

1. Provider authentication rejection returns 500 `configuration_error`; other provider 4xx returns 502; provider 5xx or connection failure returns 503.
2. Conflicting import history earns 0 credibility points, even for an otherwise identified B2B buyer.
3. Weekly recurrence converts at 4 per month (`interval_months = 0.25`), a conservative lower bound.
4. A `named_brand` product fact needs at least one quote that names Coca-Cola/Coke, Monster, or Red Bull; otherwise the extraction is rejected with 502.
5. Only confirmed personal use applies the 39 cap; conflicting purpose does not cap the score.
6. Empty message text returns 422; extra request fields such as `country` are accepted and ignored.
7. The 20,000-character limit applies to the total text of all messages.
