import pytest
from fastapi.testclient import TestClient

from app import extraction as extraction_module
from app.main import app
from tests.helpers import FakeClient, parsed_response


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def provider(monkeypatch):
    """Install a fake provider client. Call with an Extraction, a response object, or an exception."""
    created: list[FakeClient] = []

    def install(outcome, delay: float = 0.0) -> list[FakeClient]:
        if outcome is not None and not isinstance(outcome, BaseException) and not hasattr(outcome, "output_parsed"):
            outcome = parsed_response(outcome)

        def factory(api_key):
            fake = FakeClient(outcome, delay)
            created.append(fake)
            return fake

        monkeypatch.setattr(extraction_module, "_make_client", factory)
        return created

    return install
