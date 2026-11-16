"""Deterministic rubric, cap, volume, license and tier tests on mocked extractions."""

import itertools
import re

import pytest

from app.evidence import validate_extraction
from app.extraction_schema import ImportHistoryFact, LicenseFact, ProductFact, PurposeFact, VolumeFact
from app.rationale import build_rationale
from app.scoring import score_extraction, tier_for
from tests.helpers import BASE_CONVERSATION, ev, full_extraction, unknown, volume

LIC_EV = [ev(4, "We hold a valid import license")]
TWO_LEAD_EV = [ev(4, "We hold a valid import license"), ev(2, "We need 2-3 FCL per month")]


def lic(status):
    if status == "unknown":
        return unknown(LicenseFact)
    return LicenseFact(status=status, evidence=TWO_LEAD_EV if status == "conflicting" else LIC_EV)


def prod(status):
    if status == "unknown":
        return unknown(ProductFact)
    if status == "conflicting":
        return ProductFact(status=status, evidence=[ev(0, "Red Bull"), ev(3, "importing")])
    return ProductFact(status=status, evidence=[ev(0, "Red Bull and Coca-Cola")])


def purpose(status):
    if status == "unknown":
        return unknown(PurposeFact)
    if status == "conflicting":
        return PurposeFact(status=status, evidence=[ev(0, "for resale"), ev(3, "50 stores")])
    return PurposeFact(status=status, evidence=[ev(0, "for resale")])


def run(extraction):
    validate_extraction(extraction, BASE_CONVERSATION)  # fixtures stay structurally valid
    return score_extraction(extraction)


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


# --- full baseline -----------------------------------------------------------------------------

def test_full_signals_score_100_hot():
    r = run(full_extraction())
    assert (r.subtotal, r.score, r.tier, r.routing) == (100, 100, "Hot", "kam_handoff")


# --- product caps --------------------------------------------------------------------------------

def test_unrelated_product_other_signals_80_capped_to_39_cold():
    r = run(full_extraction(product=ProductFact(status="unrelated", evidence=[ev(0, "Coastline Wholesale")])))
    assert r.subtotal == 80
    assert (r.score, r.tier, r.routing) == (39, "Cold", "auto_archive")


def test_unknown_product_other_signals_80_capped_to_79_warm():
    r = run(full_extraction(product=unknown(ProductFact)))
    assert r.subtotal == 80
    assert (r.score, r.tier, r.routing) == (79, "Warm", "nurture_pool")


def test_conflicting_product_capped_to_79():
    r = run(full_extraction(product=prod("conflicting")))
    assert (r.subtotal, r.score, r.tier) == (80, 79, "Warm")


def test_other_beverage_partial_fit():
    r = run(full_extraction(product=ProductFact(status="other_beverage", evidence=[ev(0, "Red Bull")])))
    assert r.product_points == 10 and r.score == 90 and r.tier == "Hot"


def test_personal_use_capped_to_39():
    r = run(full_extraction(purpose=PurposeFact(status="personal", evidence=[ev(0, "for resale")])))
    assert (r.subtotal, r.score, r.tier, r.routing) == (100, 39, "Cold", "auto_archive")


# --- volume ranges and normalization ------------------------------------------------------------

@pytest.mark.parametrize(
    "lower,upper,expected_score,tier",
    [(0.5, 1.5, 75, "Warm"), (1, 2, 85, "Hot"), (2, 3, 100, "Hot")],
)
def test_volume_ranges_with_full_other_evidence(lower, upper, expected_score, tier):
    r = run(full_extraction(volume=volume(lower, upper)))
    assert (r.score, r.tier) == (expected_score, tier)


@pytest.mark.parametrize(
    "fact,points",
    [
        (volume(0, 0), 0),                                   # zero
        (volume(0.5, 0.5), 10),                              # sub-1
        (volume(1, 1), 20),                                  # exact 1
        (volume(2, 2), 35),                                  # exact 2
        (volume(1.99, 3), 20),                               # just below 2
        (volume(3, 3, recurrence="one_off", interval=None), 0),       # one-off
        (volume(5, 5, recurrence="unspecified", interval=None), 0),   # no stated recurrence
        (volume(None, 3), 0),                                # "up to 3 FCL/month"
        (unknown(VolumeFact), 0),                            # missing
        (VolumeFact(status="conflicting", fcl_lower=None, fcl_upper=None, recurrence="unspecified",
                    interval_months=None, evidence=[ev(2, "2-3 FCL"), ev(3, "50 stores")]), 0),  # conflicting
    ],
    ids=["zero", "sub1", "exact1", "exact2", "below2", "one_off", "unspecified", "upper_only", "missing", "conflicting"],
)
def test_volume_cases(fact, points):
    assert run(full_extraction(volume=fact)).volume_points == points


@pytest.mark.parametrize(
    "lower,interval,monthly,points",
    [(6, 3, 2, 35), (3, 2, 1.5, 20), (1, 2, 0.5, 10), (12, 12, 1, 20), (3, 3, 1, 20), (1, 0.25, 4, 35)],
    ids=["6_per_quarter", "3_per_2_months", "1_per_2_months", "12_per_year", "3_per_quarter", "1_per_week"],
)
def test_multi_month_recurrence_arithmetic(lower, interval, monthly, points):
    r = run(full_extraction(volume=volume(lower, lower, interval=interval)))
    assert r.monthly_fcl == pytest.approx(monthly)
    assert r.volume_points == points


# --- credibility -------------------------------------------------------------------------------

def test_credibility_levels():
    assert run(full_extraction()).credibility_points == 30
    no_years = ImportHistoryFact(status="has_history", years=None, evidence=[ev(3, "importing")])
    assert run(full_extraction(import_history=no_years)).credibility_points == 15
    two_years = ImportHistoryFact(status="has_history", years=2, evidence=[ev(3, "importing")])
    assert run(full_extraction(import_history=two_years)).credibility_points == 15
    assert run(full_extraction(distribution_network=unknown(type(full_extraction().distribution_network)))).credibility_points == 15
    new = ImportHistoryFact(status="no_history", years=None, evidence=[ev(3, "importing")])
    assert run(full_extraction(import_history=new)).credibility_points == 5
    assert run(full_extraction(import_history=unknown(ImportHistoryFact),
                               business_identity=unknown(type(full_extraction().business_identity)))).credibility_points == 0
    conflicting = ImportHistoryFact(status="conflicting", years=None,
                                    evidence=[ev(3, "importing for 8 years"), ev(0, "Coastline Wholesale")])
    assert run(full_extraction(import_history=conflicting)).credibility_points == 0


# --- license ----------------------------------------------------------------------------------

def test_unknown_license_can_be_hot_at_85():
    r = run(full_extraction(license=unknown(LicenseFact)))
    assert (r.subtotal, r.score, r.tier, r.routing) == (85, 85, "Hot", "kam_handoff")
    assert "unknown" in build_rationale(full_extraction(license=unknown(LicenseFact)), r).lower()


@pytest.mark.parametrize("status,subtotal", [("pending", 90), ("absent", 85), ("conflicting", 85)])
def test_pending_absent_conflicting_license_cannot_be_hot(status, subtotal):
    r = run(full_extraction(license=lic(status)))
    assert r.subtotal == subtotal  # rubric subtotal differs per status (pending earns 5)
    assert (r.score, r.tier, r.routing) == (79, "Warm", "nurture_pool")


def test_held_license_rationale_says_reported_not_verified():
    e = full_extraction()
    text = build_rationale(e, score_extraction(e))
    assert "reported" in text and "not verified" in text


# --- tiers and cap combinations ------------------------------------------------------------------

@pytest.mark.parametrize(
    "score,tier,routing",
    [(0, "Cold", "auto_archive"), (39, "Cold", "auto_archive"), (40, "Warm", "nurture_pool"),
     (79, "Warm", "nurture_pool"), (80, "Hot", "kam_handoff"), (100, "Hot", "kam_handoff")],
)
def test_tier_boundaries(score, tier, routing):
    assert tier_for(score) == (tier, routing)


def test_boundary_40_from_rubric():
    # named brand + exactly 1 FCL/month, everything else unknown -> 40 Warm.
    e = full_extraction(volume=volume(1, 1), import_history=unknown(ImportHistoryFact),
                        distribution_network=unknown(type(full_extraction().distribution_network)),
                        business_identity=unknown(type(full_extraction().business_identity)),
                        license=unknown(LicenseFact))
    r = run(e)
    assert (r.score, r.tier) == (40, "Warm")


PRODUCTS = ["named_brand", "other_beverage", "unrelated", "unknown", "conflicting"]
PURPOSES = ["business", "personal", "unknown", "conflicting"]
LICENSES = ["held", "pending", "absent", "unknown", "conflicting"]


def spec_cap(product, purpose_status, license_status):
    """Caps written directly from the spec text; the lowest applies."""
    caps = []
    if product == "unrelated" or purpose_status == "personal":
        caps.append(39)
    if product in ("unknown", "conflicting"):
        caps.append(79)
    if license_status in ("pending", "absent", "conflicting"):
        caps.append(79)
    return min(caps) if caps else None


@pytest.mark.parametrize("p,u,l", list(itertools.product(PRODUCTS, PURPOSES, LICENSES)))
def test_every_cap_combination(p, u, l):
    e = full_extraction(product=prod(p), purpose=purpose(u), license=lic(l))
    r = run(e)
    expected_subtotal = {"named_brand": 20, "other_beverage": 10}.get(p, 0) + 35 + 30 + {"held": 15, "pending": 5}.get(l, 0)
    assert r.subtotal == expected_subtotal
    cap = spec_cap(p, u, l)
    expected = expected_subtotal if cap is None else min(expected_subtotal, cap)
    assert r.score == expected
    assert (r.tier, r.routing) == tier_for(expected)
    text = build_rationale(e, r)
    assert 1 <= len(sentences(text)) <= 2
    if cap is not None and cap < expected_subtotal:
        assert f"Capped at {cap}" in text
