from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_review_case(client) -> str:
    sample_path = Path("data/samples/sample_territorial_outlier.csv")
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_evidence", "execution_mode": "EXPLORATORY"},
            files={"file": ("sample_evidence_territorial.csv", fh, "text/csv")},
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
    assert cases_payload["data"]["total"] >= 1
    return cases_payload["data"]["items"][0]["review_case_id"]


@pytest.mark.integration
def test_generate_and_get_evidence_items():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    generate_payload = client.post(f"/review-cases/{review_case_id}/evidence-items/generate").json()
    assert generate_payload["success"] is True
    assert generate_payload["data"]["evidence_items_created"] >= 1

    items_payload = client.get(f"/review-cases/{review_case_id}/evidence-items").json()
    assert items_payload["success"] is True
    assert items_payload["data"]["total"] >= 1

    evidence_types = {item["evidence_type"] for item in items_payload["data"]["items"]}
    assert "SCORE_COMPONENT" in evidence_types
    assert any(
        item["evidence_type"] in {"TURNOUT_ANOMALY", "CONCENTRATION_ANOMALY", "TERRITORIAL_OUTLIER"}
        for item in items_payload["data"]["items"]
    )

    assert all("fraude confirmado" not in item["description"].lower() for item in items_payload["data"]["items"])


@pytest.mark.integration
def test_agent_context_contains_traceability_and_limits():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    context_payload = client.get(f"/review-cases/{review_case_id}/agent-context").json()
    assert context_payload["success"] is True

    data = context_payload["data"]
    assert data["review_case"]["review_case_id"] == review_case_id
    assert len(data["evidence_items"]) >= 1
    assert len(data["score_components"]) >= 1
    assert data["traceability"]["pipeline_version"] == "0.1.0"
    assert len(data["traceability"]["source_files"]) >= 1
    assert any("no concluye fraude electoral" in limit.lower() for limit in data["methodological_limits"])
