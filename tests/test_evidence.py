"""Evidence integrity and consistency checks: rejections raise ExtractionFailed (HTTP 502)."""

import pytest

from app.errors import ExtractionFailed
from app.evidence import validate_extraction
from app.extraction_schema import ImportHistoryFact, LicenseFact, ProductFact, PurposeFact
from app.models import Message
from app.scoring import score_extraction
from tests.helpers import BASE_CONVERSATION, ev, full_extraction, unknown, volume


def check(extraction, conversation=BASE_CONVERSATION):
    validate_extraction(extraction, conversation)


def rejects(extraction, conversation=BASE_CONVERSATION, match=None):
    with pytest.raises(ExtractionFailed, match=match):
        check(extraction, conversation)


def test_valid_baseline_passes():
    check(full_extraction())


@pytest.mark.parametrize(
    "bad_evidence",
    [
        [ev(4, "We hold a valid import license and a distributor permit")],  # fabricated quote
        [ev(4, "we hold a valid import license")],                            # not exact (case)
        [ev(4, "")],                                                          # empty quote
        [ev(4, "   ")],                                                       # whitespace quote
        [ev(5, "We hold")],                                                   # index out of range
        [ev(-1, "We hold")],                                                  # negative index
        [],                                                                   # missing evidence
    ],
    ids=["fabricated", "inexact", "empty", "blank", "out_of_range", "negative", "missing"],
)
def test_invalid_evidence_rejected(bad_evidence):
    rejects(full_extraction(license=LicenseFact(status="held", evidence=bad_evidence)), match="^Extraction failed validation: license ")


def test_agent_only_assertion_does_not_establish_fact():
    convo = [
        Message(role="lead", text="Hi, we want Red Bull."),
        Message(role="agent", text="I assume you hold an import license."),
        Message(role="lead", text="What are your prices?"),
    ]
    e = full_extraction(
        product=ProductFact(status="named_brand", evidence=[ev(0, "Red Bull")]),
        volume=volume(None, None, status="unknown", recurrence="unspecified", interval=None, evidence=[]),
        import_history=unknown(ImportHistoryFact),
        distribution_network=unknown(type(full_extraction().distribution_network)),
        business_identity=unknown(type(full_extraction().business_identity)),
        purpose=unknown(PurposeFact),
        license=LicenseFact(status="held", evidence=[ev(1, "I assume you hold an import license")]),
    )
    rejects(e, convo, match="license relies on an agent message without a cited buyer confirmation")
    # Agent message + an uncited, unrelated buyer reply is still not a confirmation.
    e2 = e.model_copy(update={"license": LicenseFact(
        status="held", evidence=[ev(1, "I assume you hold an import license"), ev(0, "Red Bull")])})
    rejects(e2, convo, match="license relies on an agent message")


def test_contextual_buyer_confirmation_keeps_buyer_evidence():
    convo = [
        Message(role="lead", text="Hi, we want Red Bull."),
        Message(role="agent", text="Do you hold a valid import license?"),
        Message(role="lead", text="Yes"),
    ]
    e = full_extraction(
        product=ProductFact(status="named_brand", evidence=[ev(0, "Red Bull")]),
        volume=volume(None, None, status="unknown", recurrence="unspecified", interval=None, evidence=[]),
        import_history=unknown(ImportHistoryFact),
        distribution_network=unknown(type(full_extraction().distribution_network)),
        business_identity=unknown(type(full_extraction().business_identity)),
        purpose=unknown(PurposeFact),
        license=LicenseFact(status="held", evidence=[ev(1, "Do you hold a valid import license?"), ev(2, "Yes")]),
    )
    check(e, convo)
    assert score_extraction(e).license_points == 15
    # The buyer's "Yes" alone is also acceptable evidence.
    check(e.model_copy(update={"license": LicenseFact(status="held", evidence=[ev(2, "Yes")])}), convo)


def test_unknown_fact_with_evidence_rejected():
    rejects(full_extraction(license=LicenseFact(status="unknown", evidence=[ev(4, "We hold")])), match="license is unknown but cites")


def test_conflicting_license_keeps_both_buyer_claims():
    convo = BASE_CONVERSATION + [Message(role="lead", text="Actually our license expired last year.")]
    conflict = LicenseFact(status="conflicting",
                           evidence=[ev(4, "We hold a valid import license"), ev(5, "our license expired")])
    e = full_extraction(license=conflict)
    check(e, convo)
    assert [x.message_index for x in e.license.evidence] == [4, 5]
    r = score_extraction(e)
    assert r.license_points == 0 and r.score == 79 and r.tier == "Warm"
    # A "conflict" citing only one buyer claim is rejected.
    rejects(full_extraction(license=LicenseFact(status="conflicting", evidence=[ev(4, "We hold")])), convo, match="does not cite two buyer claims")


def test_clear_later_correction_resolves_conflict():
    convo = [
        Message(role="lead", text="We want Red Bull. Our import license is pending."),
        Message(role="lead", text="Update: as of 1 November our import license was approved and is now active."),
    ]
    e = full_extraction(
        product=ProductFact(status="named_brand", evidence=[ev(0, "Red Bull")]),
        volume=volume(None, None, status="unknown", recurrence="unspecified", interval=None, evidence=[]),
        import_history=unknown(ImportHistoryFact),
        distribution_network=unknown(type(full_extraction().distribution_network)),
        business_identity=unknown(type(full_extraction().business_identity)),
        purpose=unknown(PurposeFact),
        license=LicenseFact(status="held", evidence=[ev(1, "our import license was approved and is now active")]),
    )
    check(e, convo)
    assert score_extraction(e).license_points == 15


@pytest.mark.parametrize(
    "fact",
    [
        volume(3, 2),                                                  # reversed range
        volume(-1, 2),                                                 # negative quantity
        volume(None, None),                                            # stated without quantity
        volume(1, 1, recurrence="recurring", interval=None),           # recurring without interval
        volume(1, 1, recurrence="recurring", interval=0),              # impossible interval
        volume(1, 1, recurrence="recurring", interval=-1),             # negative interval
        volume(1, 1, recurrence="one_off", interval=1),                # interval on one-off
        volume(1, 1, recurrence="recurring", interval=float("nan")),   # non-finite
        volume(2, 3, status="unknown"),                                # unknown with quantities/evidence
        volume(2, 3, status="conflicting",
               evidence=[ev(2, "2-3 FCL"), ev(3, "50 stores")]),      # conflicting with quantities
    ],
    ids=["reversed", "negative", "no_quantity", "no_interval", "zero_interval", "negative_interval",
         "interval_on_one_off", "nan", "unknown_with_values", "conflicting_with_values"],
)
def test_inconsistent_volume_rejected(fact):
    rejects(full_extraction(volume=fact), match="validation: volume ")


def test_inconsistent_history_rejected():
    rejects(full_extraction(import_history=ImportHistoryFact(status="no_history", years=5,
                                                             evidence=[ev(3, "importing")])), match="import_history")
    rejects(full_extraction(import_history=ImportHistoryFact(status="has_history", years=-2,
                                                             evidence=[ev(3, "importing")])), match="import_history")


def test_evidence_less_negative_status_becomes_unknown():
    # Seen live on S002: the model reported distribution "absent" from silence.
    from app.extraction_schema import DistributionFact

    e = full_extraction(
        distribution_network=DistributionFact(status="absent", evidence=[]),
        license=LicenseFact(status="absent", evidence=[]),
        import_history=ImportHistoryFact(status="no_history", years=None, evidence=[]),
    )
    check(e)
    assert e.distribution_network.status == "unknown"
    assert e.license.status == "unknown"
    assert e.import_history.status == "unknown"


def test_negative_status_with_bad_evidence_still_rejected():
    rejects(full_extraction(license=LicenseFact(status="absent", evidence=[ev(4, "not in the text")])),
            match="validation: license ")


def test_other_evidence_less_known_status_still_rejected():
    rejects(full_extraction(purpose=PurposeFact(status="personal", evidence=[])), match="validation: purpose ")


def test_named_brand_requires_brand_in_evidence():
    rejects(full_extraction(product=ProductFact(status="named_brand", evidence=[ev(0, "Coastline Wholesale")])), match="no evidence quote names a listed brand")
    check(full_extraction(product=ProductFact(status="named_brand", evidence=[ev(0, "Coca-Cola")])))
