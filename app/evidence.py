"""Evidence integrity and cross-field consistency checks on an extraction.

These are structural checks: they prove each cited quote exists in the cited
message and that buyer facts rest on buyer messages. They cannot prove that a
quote semantically supports the interpretation; labeled extraction evals cover that.
Any failure raises ExtractionFailed (HTTP 502). One normalization runs first: a
negative status ("absent", "no_history") with no evidence at all means the buyer
said nothing, which the extraction rules define as "unknown", so it is recorded as
unknown. Everything else that fails is rejected, never downgraded.
"""

import math
import re

from app.errors import ExtractionFailed
from app.extraction_schema import Extraction
from app.models import Message

MAX_FCL = 10_000.0
MAX_INTERVAL_MONTHS = 120.0
MAX_YEARS = 150.0

# Normalized (lowercase, alphanumerics only) brand tokens for the named-brand policy list.
_BRAND_TOKENS = ("cocacola", "coke", "monster", "redbull")


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _fail(fact: str, reason: str) -> None:
    raise ExtractionFailed(f"Extraction failed validation: {fact} {reason}.")


def _check_evidence(name: str, fact, conversation: list[Message]) -> None:
    status = fact.status
    evidence = fact.evidence

    if status == "unknown":
        if evidence:
            _fail(name, "is unknown but cites affirmative evidence")
        return

    if not evidence:
        _fail(name, f"is {status} but has no evidence")

    cited = {e.message_index for e in evidence}
    lead_entries = set()
    for e in evidence:
        if not (0 <= e.message_index < len(conversation)):
            _fail(name, "cites a message index outside the transcript")
        if not e.quote.strip():
            _fail(name, "cites an empty quote")
        message = conversation[e.message_index]
        if e.quote not in message.text:
            _fail(name, "cites a quote that is not an exact substring of the cited message")
        if message.role == "lead":
            lead_entries.add((e.message_index, e.quote))
        else:
            # Agent text is allowed only as context for an immediately following,
            # also-cited buyer confirmation (e.g. agent asks, lead says "yes").
            nxt = e.message_index + 1
            if not (nxt < len(conversation) and conversation[nxt].role == "lead" and nxt in cited):
                _fail(name, "relies on an agent message without a cited buyer confirmation")

    if not lead_entries:
        _fail(name, "has no evidence from a lead message")
    if status == "conflicting" and len(lead_entries) < 2:
        _fail(name, "is conflicting but does not cite two buyer claims")


def _finite(value: float | None) -> bool:
    return value is None or math.isfinite(value)


def _check_volume(extraction: Extraction) -> None:
    v = extraction.volume
    for value in (v.fcl_lower, v.fcl_upper, v.interval_months):
        if not _finite(value):
            _fail("volume", "contains a non-finite number")

    if v.status in ("unknown", "conflicting"):
        if v.fcl_lower is not None or v.fcl_upper is not None or v.interval_months is not None:
            _fail("volume", f"is {v.status} but carries quantities")
        if v.status == "unknown" and v.recurrence != "unspecified":
            _fail("volume", "is unknown but states a recurrence")
        return

    # status == "stated"
    if v.fcl_lower is None and v.fcl_upper is None:
        _fail("volume", "is stated without any quantity")
    for value in (v.fcl_lower, v.fcl_upper):
        if value is not None and not (0 <= value <= MAX_FCL):
            _fail("volume", "has an out-of-range quantity")
    if v.fcl_lower is not None and v.fcl_upper is not None and v.fcl_lower > v.fcl_upper:
        _fail("volume", "has a reversed range")
    if v.recurrence == "recurring":
        if v.interval_months is None or not (0 < v.interval_months <= MAX_INTERVAL_MONTHS):
            _fail("volume", "is recurring without a valid interval")
    elif v.interval_months is not None:
        _fail("volume", "has an interval but is not recurring")


def _check_history(extraction: Extraction) -> None:
    h = extraction.import_history
    if not _finite(h.years):
        _fail("import_history", "contains a non-finite number")
    if h.years is not None:
        if h.status != "has_history":
            _fail("import_history", f"is {h.status} but states years")
        if not (0 < h.years <= MAX_YEARS):
            _fail("import_history", "has an out-of-range number of years")


def _check_product(extraction: Extraction) -> None:
    p = extraction.product
    if p.status == "named_brand":
        quotes = _normalize(" ".join(e.quote for e in p.evidence))
        if not any(token in quotes for token in _BRAND_TOKENS):
            _fail("product", "is named_brand but no evidence quote names a listed brand")


_SILENCE_STATUSES = {
    "distribution_network": "absent",
    "license": "absent",
    "import_history": "no_history",
}


def _normalize_silence(extraction: Extraction) -> None:
    """Treat an evidence-less negative status as unknown (the buyer said nothing)."""
    facts = extraction.facts()
    for name, negative in _SILENCE_STATUSES.items():
        fact = facts[name]
        if fact.status == negative and not fact.evidence:
            fact.status = "unknown"
            if name == "import_history":
                fact.years = None


def validate_extraction(extraction: Extraction, conversation: list[Message]) -> None:
    _normalize_silence(extraction)
    for name, fact in extraction.facts().items():
        _check_evidence(name, fact, conversation)
    _check_volume(extraction)
    _check_history(extraction)
    _check_product(extraction)
