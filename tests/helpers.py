"""Builders for mocked extractions and fake provider clients."""

import asyncio
from types import SimpleNamespace

from app.extraction_schema import (
    BusinessIdentityFact,
    DistributionFact,
    Evidence,
    Extraction,
    ImportHistoryFact,
    LicenseFact,
    ProductFact,
    PurposeFact,
    VolumeFact,
)
from app.models import Message

# Generic transcript containing every quote used by `full_extraction`.
BASE_CONVERSATION = [
    Message(role="lead", text="We are Coastline Wholesale and want Red Bull and Coca-Cola for resale."),
    Message(role="agent", text="How much volume do you need?"),
    Message(role="lead", text="We need 2-3 FCL per month, ongoing."),
    Message(role="lead", text="We have been importing for 8 years through our own distribution network of 50 stores."),
    Message(role="lead", text="We hold a valid import license."),
]


def ev(index: int, quote: str) -> Evidence:
    return Evidence(message_index=index, quote=quote)


def unknown(cls):
    extra = {}
    if cls is VolumeFact:
        extra = dict(fcl_lower=None, fcl_upper=None, recurrence="unspecified", interval_months=None)
    if cls is ImportHistoryFact:
        extra = dict(years=None)
    return cls(status="unknown", evidence=[], **extra)


def volume(lower, upper, recurrence="recurring", interval=1.0, status="stated", evidence=None):
    return VolumeFact(
        status=status,
        fcl_lower=lower,
        fcl_upper=upper,
        recurrence=recurrence,
        interval_months=interval,
        evidence=evidence if evidence is not None else [ev(2, "2-3 FCL per month")],
    )


def full_extraction(**overrides) -> Extraction:
    """Every factor at maximum (subtotal 100) unless overridden; valid against BASE_CONVERSATION."""
    facts = dict(
        product=ProductFact(status="named_brand", evidence=[ev(0, "Red Bull and Coca-Cola")]),
        volume=volume(2, 3),
        import_history=ImportHistoryFact(status="has_history", years=8, evidence=[ev(3, "importing for 8 years")]),
        distribution_network=DistributionFact(status="present", evidence=[ev(3, "our own distribution network of 50 stores")]),
        business_identity=BusinessIdentityFact(status="identified", evidence=[ev(0, "Coastline Wholesale")]),
        license=LicenseFact(status="held", evidence=[ev(4, "We hold a valid import license")]),
        purpose=PurposeFact(status="business", evidence=[ev(0, "for resale")]),
    )
    facts.update(overrides)
    return Extraction(**facts)


class FakeResponses:
    def __init__(self, outcome, delay: float = 0.0):
        self.outcome = outcome
        self.delay = delay
        self.calls = []
        self.cancelled = False

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            try:
                await asyncio.sleep(self.delay)
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome, delay: float = 0.0):
        self.responses = FakeResponses(outcome, delay)
        self.closed = False

    async def close(self):
        self.closed = True


def parsed_response(extraction: Extraction | None, *, refusal: bool = False, status: str = "completed"):
    output = []
    if refusal:
        output = [SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal", refusal="no")])]
    return SimpleNamespace(status=status, output=output, output_parsed=extraction)
