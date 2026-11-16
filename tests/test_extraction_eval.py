"""Real-provider extraction eval on the acceptance samples.

Skipped unless OPENAI_API_KEY is set. Asserts extracted facts independently of the final
score, then the policy outputs. Run: pytest -m eval -s
Transcripts in tests/fixtures.py are the brief's original sample payloads.
"""

import asyncio
import os

import pytest

from app.evidence import validate_extraction
from app.extraction import extract
from app.models import ScoreRequest
from app.scoring import score_extraction
from tests.fixtures import REQUIRED_FACTS, SAMPLES

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set; real eval skipped"),
]


@pytest.mark.parametrize("sample_id", list(SAMPLES))
def test_real_extraction_matches_required_facts(sample_id):
    request = ScoreRequest(**SAMPLES[sample_id]["request"])
    extraction = asyncio.run(extract(request.conversation))
    validate_extraction(extraction, request.conversation)
    result = score_extraction(extraction)
    print(f"\n{sample_id}: {extraction.model_dump_json()}\n-> {result.score} {result.tier}")

    facts = REQUIRED_FACTS[sample_id]
    assert extraction.product.status == facts["product"]
    assert result.monthly_fcl == facts["monthly_fcl"]
    assert extraction.import_history.status == facts["history"]
    assert extraction.license.status == facts["license"]
    if "volume_upper" in facts:
        assert extraction.volume.fcl_upper == facts["volume_upper"]
    if "years_min" in facts:
        assert (extraction.import_history.years or 0) >= facts["years_min"]
    if "network" in facts:
        assert extraction.distribution_network.status == facts["network"]
    if "purpose" in facts:
        assert extraction.purpose.status == facts["purpose"]
    if "identity" in facts:
        assert extraction.business_identity.status == facts["identity"]

    expected = SAMPLES[sample_id]["expected"]
    assert (result.score, result.tier, result.routing) == (expected["score"], expected["tier"], expected["routing"])
