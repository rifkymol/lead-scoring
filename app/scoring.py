"""Deterministic scoring, caps, tier and routing from a validated extraction."""

from dataclasses import dataclass, field

from app.extraction_schema import Extraction

CAP_UNRELATED_OR_PERSONAL = 39
CAP_UNCERTAIN = 79


@dataclass(frozen=True)
class Cap:
    limit: int
    reason: str  # short machine-readable reason, rendered by app/rationale.py


@dataclass(frozen=True)
class ScoreResult:
    product_points: int
    volume_points: int
    credibility_points: int
    license_points: int
    monthly_fcl: float | None
    subtotal: int
    caps: list[Cap] = field(default_factory=list)
    score: int = 0
    tier: str = "Cold"
    routing: str = "auto_archive"

    @property
    def binding_cap(self) -> Cap | None:
        """The lowest cap, if it actually reduced the subtotal."""
        if not self.caps:
            return None
        lowest = min(self.caps, key=lambda c: c.limit)
        return lowest if lowest.limit < self.subtotal else None


def product_points(extraction: Extraction) -> int:
    return {"named_brand": 20, "other_beverage": 10}.get(extraction.product.status, 0)


def monthly_fcl_lower(extraction: Extraction) -> float | None:
    """Committed recurring monthly FCL lower bound, or None when it earns nothing."""
    v = extraction.volume
    if v.status != "stated" or v.recurrence != "recurring":
        return None
    if v.fcl_lower is None or v.fcl_lower <= 0 or not v.interval_months:
        return None
    return round(v.fcl_lower / v.interval_months, 9)


def volume_points(monthly: float | None) -> int:
    if monthly is None or monthly <= 0:
        return 0
    if monthly >= 2:
        return 35
    if monthly >= 1:
        return 20
    return 10


def credibility_points(extraction: Extraction) -> int:
    history = extraction.import_history
    if history.status == "has_history":
        established = (
            history.years is not None
            and history.years >= 3
            and extraction.distribution_network.status == "present"
        )
        return 30 if established else 15
    if history.status == "conflicting":
        return 0
    if extraction.business_identity.status == "identified":
        return 5
    return 0


def license_points(extraction: Extraction) -> int:
    return {"held": 15, "pending": 5}.get(extraction.license.status, 0)


def applicable_caps(extraction: Extraction) -> list[Cap]:
    caps: list[Cap] = []
    if extraction.product.status == "unrelated":
        caps.append(Cap(CAP_UNRELATED_OR_PERSONAL, "unrelated_product"))
    if extraction.purpose.status == "personal":
        caps.append(Cap(CAP_UNRELATED_OR_PERSONAL, "personal_use"))
    if extraction.product.status in ("unknown", "conflicting"):
        caps.append(Cap(CAP_UNCERTAIN, f"product_{extraction.product.status}"))
    if extraction.license.status in ("pending", "absent", "conflicting"):
        caps.append(Cap(CAP_UNCERTAIN, f"license_{extraction.license.status}"))
    return caps


def tier_for(score: int) -> tuple[str, str]:
    if score >= 80:
        return "Hot", "kam_handoff"
    if score >= 40:
        return "Warm", "nurture_pool"
    return "Cold", "auto_archive"


def score_extraction(extraction: Extraction) -> ScoreResult:
    monthly = monthly_fcl_lower(extraction)
    parts = (
        product_points(extraction),
        volume_points(monthly),
        credibility_points(extraction),
        license_points(extraction),
    )
    subtotal = sum(parts)
    caps = applicable_caps(extraction)
    final = min([subtotal, *(c.limit for c in caps)])
    final = max(0, min(100, int(final)))
    tier, routing = tier_for(final)
    return ScoreResult(*parts, monthly_fcl=monthly, subtotal=subtotal, caps=caps,
                       score=final, tier=tier, routing=routing)
