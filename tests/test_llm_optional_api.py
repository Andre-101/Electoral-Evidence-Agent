from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_review_case(client) -> str:
    sample_path = Path("data/samples/sample_territorial_outlier.csv")
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_llm_optional", "execution_mode": "EXPLORATORY"},
            files={"file": ("sample_llm_optional.csv", fh, "text/csv")},
        )
    payload = response.json()
    assert payload["success"] is True
    ingestion_run_id = payload["data"]["ingestion_run_id"]

    assert client.post(f"/ingestions/{ingestion_run_id}/profile").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/map", json={}).json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/load-core").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/calculate-basic-metrics").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/calculate-territorial-metrics").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/generate-eda-alerts").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/calculate-scores").json()["success"] is True

    cases_payload = client.get(f"/ingestions/{ingestion_run_id}/review-cases").json()
    assert cases_payload["success"] is True
    review_case_id = cases_payload["data"]["items"][0]["review_case_id"]
    assert client.post(f"/review-cases/{review_case_id}/evidence-items/generate").json()["success"] is True
    return review_case_id


def test_llm_status_endpoint_is_optional():
    client = get_test_client()
    payload = client.get("/llm/status").json()
    assert payload["success"] is True
    assert payload["data"]["provider"] == "anthropic"
    assert payload["data"]["required"] is False
    assert "api_key_configured" in payload["data"]


@pytest.mark.integration
def test_dossier_forced_without_llm_still_works():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    payload = client.post(f"/review-cases/{review_case_id}/dossier?force_regenerate=true&use_llm=false").json()
    assert payload["success"] is True
    assert payload["data"]["dossier_status"] == "GENERATED"
    assert payload["data"]["generated_by"] == "deterministic_agent_v0.1"
    assert payload["data"]["llm"]["llm_requested"] is False
    assert payload["data"]["llm"]["llm_used"] is False


@pytest.mark.integration
def test_dossier_llm_requested_is_optional_and_safe():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    status_payload = client.get("/llm/status").json()
    api_key_configured = status_payload["data"]["api_key_configured"]

    payload = client.post(f"/review-cases/{review_case_id}/dossier?force_regenerate=true&use_llm=true").json()
    assert payload["success"] is True
    assert payload["data"]["dossier_status"] == "GENERATED"
    assert payload["data"]["llm"]["llm_requested"] is True

    if api_key_configured:
        # If a key exists, the correct behavior is to allow Claude.
        assert payload["data"]["generated_by"].startswith("claude_llm:") or payload["data"]["generated_by"] == "deterministic_agent_v0.1"
    else:
        # Without a key, the correct behavior is deterministic fallback.
        assert payload["data"]["generated_by"] == "deterministic_agent_v0.1"
        assert payload["data"]["llm"]["llm_used"] is False
