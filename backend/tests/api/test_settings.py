import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.session import clear_all_sessions

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_get_llm_provider_default(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    response = client.get("/api/settings/llm-provider")
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "ollama"

    providers = {p["id"]: p for p in data["providers"]}
    assert "ollama" in providers
    assert providers["ollama"]["configured"] is True
    assert "groq" in providers
    assert providers["groq"]["configured"] is False


def test_post_llm_provider_unconfigured(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.post("/api/settings/llm-provider", json={"provider": "groq"})
    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


def test_post_llm_provider_configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy_test_key_12345")

    # Get settings with Groq configured
    get_res = client.get("/api/settings/llm-provider")
    assert get_res.status_code == 200
    providers = {p["id"]: p for p in get_res.json()["providers"]}
    assert providers["groq"]["configured"] is True

    # Update provider to groq
    post_res = client.post("/api/settings/llm-provider", json={"provider": "groq"})
    assert post_res.status_code == 200
    assert post_res.json()["active_provider"] == "groq"

    # Verify active provider is now groq
    get_after = client.get("/api/settings/llm-provider")
    assert get_after.json()["active_provider"] == "groq"


def test_post_invalid_provider():
    response = client.post("/api/settings/llm-provider", json={"provider": "invalid_backend"})
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]
