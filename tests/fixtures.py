"""Acceptance fixtures S001/S002/S003/L001.

Transcripts are copied verbatim from the take-home brief (test-1-build/BRIEF.md):
S001/S002/S003 are its sample payloads and L001 is its input-contract example.
The mocked extractions encode the facts in the spec's acceptance table; the real
extraction eval (tests/test_extraction_eval.py) checks a live model against them.
"""

from app.extraction_schema import (
    BusinessIdentityFact,
    DistributionFact,
    Extraction,
    ImportHistoryFact,
    LicenseFact,
    ProductFact,
    PurposeFact,
    VolumeFact,
)
from tests.helpers import ev, unknown

SAMPLES = {
    "S001": {
        "request": {
            "lead_id": "S001",
            "channel": "whatsapp",
            "conversation": [
                {"role": "lead", "text": "UAE distributor, 3 FCL/month Red Bull, 8 years importing energy drinks. Looking for original Austrian product."},
                {"role": "agent", "text": "Volume target on Red Bull specifically?"},
                {"role": "lead", "text": "2-3 FCL/month sustained. ~250 retail accounts across UAE."},
            ],
        },
        "extraction": Extraction(
            product=ProductFact(status="named_brand", evidence=[ev(0, "Red Bull")]),
            volume=VolumeFact(status="stated", fcl_lower=2, fcl_upper=3, recurrence="recurring",
                              interval_months=1, evidence=[ev(2, "2-3 FCL/month sustained")]),
            import_history=ImportHistoryFact(status="has_history", years=8,
                                             evidence=[ev(0, "8 years importing energy drinks")]),
            distribution_network=DistributionFact(status="present",
                                                  evidence=[ev(2, "~250 retail accounts across UAE")]),
            business_identity=BusinessIdentityFact(status="identified", evidence=[ev(0, "UAE distributor")]),
            license=unknown(LicenseFact),
            purpose=PurposeFact(status="business", evidence=[ev(0, "UAE distributor")]),
        ),
        "expected": {"score": 85, "tier": "Hot", "routing": "kam_handoff"},
    },
    "S002": {
        "request": {
            "lead_id": "S002",
            "channel": "email",
            "conversation": [
                {"role": "lead", "text": "hey can I get a few cans of red bull for my office party"},
            ],
        },
        "extraction": Extraction(
            product=ProductFact(status="named_brand", evidence=[ev(0, "red bull")]),
            volume=unknown(VolumeFact),
            import_history=unknown(ImportHistoryFact),
            distribution_network=unknown(DistributionFact),
            business_identity=unknown(BusinessIdentityFact),
            license=unknown(LicenseFact),
            purpose=PurposeFact(status="personal", evidence=[ev(0, "for my office party")]),
        ),
        "expected": {"score": 20, "tier": "Cold", "routing": "auto_archive"},
    },
    "S003": {
        "request": {
            "lead_id": "S003",
            "channel": "email",
            "conversation": [
                {"role": "lead", "text": "Ghana-based distributor looking for Coca-Cola products. New entrant, license in process — expected 6 weeks. Initial volume 1 FCL/month."},
            ],
        },
        "extraction": Extraction(
            product=ProductFact(status="named_brand", evidence=[ev(0, "Coca-Cola products")]),
            volume=VolumeFact(status="stated", fcl_lower=1, fcl_upper=1, recurrence="recurring",
                              interval_months=1, evidence=[ev(0, "Initial volume 1 FCL/month")]),
            import_history=ImportHistoryFact(status="no_history", years=None,
                                             evidence=[ev(0, "New entrant")]),
            distribution_network=unknown(DistributionFact),
            business_identity=BusinessIdentityFact(status="identified",
                                                   evidence=[ev(0, "Ghana-based distributor")]),
            license=LicenseFact(status="pending", evidence=[ev(0, "license in process")]),
            purpose=PurposeFact(status="business", evidence=[ev(0, "Ghana-based distributor")]),
        ),
        "expected": {"score": 50, "tier": "Warm", "routing": "nurture_pool"},
    },
    "L001": {
        "request": {
            "lead_id": "L001",
            "channel": "whatsapp",
            "conversation": [
                {"role": "lead", "text": "Hi, looking for wholesale Monster Energy supply for Singapore. 1 FCL/month."},
                {"role": "agent", "text": "Could you confirm your import license and history?"},
                {"role": "lead", "text": "Yes, licensed 4 years. Currently import 2 brands."},
            ],
        },
        "extraction": Extraction(
            product=ProductFact(status="named_brand", evidence=[ev(0, "Monster Energy")]),
            volume=VolumeFact(status="stated", fcl_lower=1, fcl_upper=1, recurrence="recurring",
                              interval_months=1, evidence=[ev(0, "1 FCL/month")]),
            import_history=ImportHistoryFact(status="has_history", years=None,
                                             evidence=[ev(2, "Currently import 2 brands")]),
            distribution_network=unknown(DistributionFact),
            business_identity=BusinessIdentityFact(status="identified",
                                                   evidence=[ev(0, "wholesale Monster Energy supply")]),
            license=LicenseFact(status="held", evidence=[ev(1, "Could you confirm your import license"),
                                                         ev(2, "Yes, licensed 4 years")]),
            purpose=PurposeFact(status="business", evidence=[ev(0, "wholesale")]),
        ),
        "expected": {"score": 70, "tier": "Warm", "routing": "nurture_pool"},
    },
}

# Spec-required extracted facts per sample, asserted against real extractions in the eval.
REQUIRED_FACTS = {
    "S001": {"product": "named_brand", "monthly_fcl": 2, "volume_upper": 3, "history": "has_history",
             "years_min": 8, "network": "present", "license": "unknown"},
    "S002": {"product": "named_brand", "purpose": "personal", "monthly_fcl": None,
             "history": "unknown", "license": "unknown"},
    "S003": {"product": "named_brand", "monthly_fcl": 1, "history": "no_history",
             "identity": "identified", "license": "pending"},
    "L001": {"product": "named_brand", "monthly_fcl": 1, "history": "has_history", "license": "held"},
}
