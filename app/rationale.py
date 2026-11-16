"""Deterministic one- or two-sentence rationale built only from validated facts.

No transcript text is echoed, so injected content cannot reach the response.
"""

from app.extraction_schema import Extraction
from app.scoring import Cap, ScoreResult

_PRODUCT = {
    "named_brand": "requests a listed brand",
    "other_beverage": "requests another beverage",
    "unrelated": "requests only non-beverage products",
    "unknown": "product not stated",
    "conflicting": "conflicting product requests",
}

_LICENSE = {
    "held": "import license reported as held (not verified)",
    "pending": "import license pending",
    "absent": "no import license",
    "unknown": "license status unknown",
    "conflicting": "conflicting license claims",
}

_CAP_SENTENCE = {
    "personal_use": "Capped at 39 because the buyer describes a personal-use purchase, not resale.",
    "unrelated_product": "Capped at 39 because the inquiry is for non-beverage products.",
    "product_unknown": "Capped at 79 because the buyer has not stated which product they want.",
    "product_conflicting": "Capped at 79 because the buyer's product requests conflict.",
    "license_pending": "Capped at 79 until the pending import license is confirmed.",
    "license_absent": "Capped at 79 because the buyer reports no import license.",
    "license_conflicting": "Capped at 79 because the buyer's license claims conflict.",
}

_NONBINDING_SENTENCE = {
    "personal_use": "Personal-use intent keeps this lead out of the KAM pipeline.",
    "unrelated_product": "Non-beverage demand keeps this lead out of the KAM pipeline.",
    "product_unknown": "The product is unconfirmed, which blocks Hot routing.",
    "product_conflicting": "Conflicting product requests block Hot routing.",
    "license_pending": "The pending license blocks Hot routing until confirmed.",
    "license_absent": "The missing import license blocks Hot routing.",
    "license_conflicting": "Conflicting license claims block Hot routing.",
}


def _num(value: float) -> str:
    return f"{value:g}"


def _volume_phrase(extraction: Extraction, result: ScoreResult) -> str:
    v = extraction.volume
    if result.monthly_fcl is not None:
        return f"{_num(result.monthly_fcl)} committed recurring FCL/month"
    if v.status == "unknown":
        return "no recurring FCL volume stated"
    if v.status == "conflicting":
        return "conflicting volume claims"
    if v.recurrence == "one_off":
        return "one-off order only"
    if v.recurrence == "unspecified":
        return "volume without a stated recurrence"
    if v.fcl_lower is None:
        return "no committed minimum volume"
    return "zero committed volume"


def _credibility_phrase(extraction: Extraction, result: ScoreResult) -> str:
    h = extraction.import_history
    if h.status == "has_history":
        years = f"{_num(h.years)} years' " if h.years is not None else ""
        network = " with a distribution network" if result.credibility_points == 30 else ""
        return f"{years}importing history{network}"
    if h.status == "conflicting":
        return "conflicting import history"
    if extraction.business_identity.status == "identified":
        return "identified B2B buyer without import history"
    return "business credibility unknown"


def _second_sentence(extraction: Extraction, result: ScoreResult) -> str | None:
    binding: Cap | None = result.binding_cap
    if binding is not None:
        return _CAP_SENTENCE[binding.reason]
    if result.caps:
        lowest = min(result.caps, key=lambda c: c.limit)
        return _NONBINDING_SENTENCE[lowest.reason]
    if extraction.license.status == "unknown":
        return "License status is unknown and should be confirmed before shipment."
    conflicts = [name for name, fact in extraction.facts().items() if fact.status == "conflicting"]
    if conflicts:
        return "Some buyer claims conflict and should be clarified."
    return None


def build_rationale(extraction: Extraction, result: ScoreResult) -> str:
    first = (
        f"{result.tier} at {result.score}/100: "
        f"{_PRODUCT[extraction.product.status]}, "
        f"{_volume_phrase(extraction, result)}, "
        f"{_credibility_phrase(extraction, result)}, "
        f"{_LICENSE[extraction.license.status]}."
    )
    second = _second_sentence(extraction, result)
    return f"{first} {second}" if second else first
