"""Structured-output schema for the single extraction call.

Kept free of numeric/length constraints so the provider's strict schema accepts it;
all bounds and cross-field rules are enforced in Python (app/evidence.py).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(_Strict):
    message_index: int = Field(description="Zero-based index of the original transcript message.")
    quote: str = Field(description="Exact, verbatim substring copied from that message's text.")


class ProductFact(_Strict):
    status: Literal["named_brand", "other_beverage", "unrelated", "unknown", "conflicting"] = Field(
        description=(
            "named_brand: buyer requests Coca-Cola (incl. Coke), Monster, or Red Bull. "
            "other_beverage: buyer requests another beverage. "
            "unrelated: buyer requests only non-beverage products. "
            "unknown: product not stated by the buyer. conflicting: unresolved incompatible buyer claims."
        )
    )
    evidence: list[Evidence]


class VolumeFact(_Strict):
    status: Literal["stated", "unknown", "conflicting"]
    fcl_lower: float | None = Field(
        description="Lower bound of FCL (full container load) quantity per interval; null if no committed lower bound (e.g. 'up to 3')."
    )
    fcl_upper: float | None = Field(description="Upper bound of FCL quantity per interval; null if none stated.")
    recurrence: Literal["recurring", "one_off", "unspecified"]
    interval_months: float | None = Field(
        description="Months covered by the stated quantity when recurring (month=1, quarter=3, year=12); null otherwise."
    )
    evidence: list[Evidence]


class ImportHistoryFact(_Strict):
    status: Literal["has_history", "no_history", "unknown", "conflicting"]
    years: float | None = Field(description="Years of importing stated by the buyer; null if not stated.")
    evidence: list[Evidence]


class DistributionFact(_Strict):
    status: Literal["present", "absent", "unknown", "conflicting"]
    evidence: list[Evidence]


class BusinessIdentityFact(_Strict):
    status: Literal["identified", "unknown", "conflicting"] = Field(
        description="identified: buyer identifies a trading, wholesale, retail, or distribution business buying for resale."
    )
    evidence: list[Evidence]


class LicenseFact(_Strict):
    status: Literal["held", "pending", "absent", "unknown", "conflicting"]
    evidence: list[Evidence]


class PurposeFact(_Strict):
    status: Literal["business", "personal", "unknown", "conflicting"] = Field(
        description="personal: purchase for personal/private consumption such as a party or event, not resale."
    )
    evidence: list[Evidence]


class Extraction(_Strict):
    product: ProductFact
    volume: VolumeFact
    import_history: ImportHistoryFact
    distribution_network: DistributionFact
    business_identity: BusinessIdentityFact
    license: LicenseFact
    purpose: PurposeFact

    def facts(self) -> dict[str, BaseModel]:
        return {
            "product": self.product,
            "volume": self.volume,
            "import_history": self.import_history,
            "distribution_network": self.distribution_network,
            "business_identity": self.business_identity,
            "license": self.license,
            "purpose": self.purpose,
        }
