from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_scored_ingestion(client, sample_path: Path, upload_name: str) -> str:
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_scoring", "execution_mode": "EXPLORATORY"},
            files={"file": (upload_name, fh, "text/csv")},
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
    return ingestion_run_id


@pytest.mark.integration
def test_calculate_scores_and_review_cases():
    client = get_test_client()
    ingestion_run_id = _prepare_scored_ingestion(
        client,
        Path("data/samples/sample_territorial_outlier.csv"),
        "sample_scoring_territorial.csv",
    )

    score_payload = client.post(f"/ingestions/{ingestion_run_id}/calculate-scores").json()
    assert score_payload["success"] is True
    assert score_payload["data"]["anomaly_scores_created"] >= 1
    assert score_payload["data"]["score_components_created"] >= 1
    assert score_payload["data"]["review_cases_created"] >= 1

    cases_payload = client.get(f"/ingestions/{ingestion_run_id}/review-cases").json()
    assert cases_payload["success"] is True
    assert cases_payload["data"]["total"] >= 1

    first_case = cases_payload["data"]["items"][0]
    assert 0 <= first_case["review_priority_score"] <= 100
    assert first_case["priority"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL_REVIEW"]
    assert first_case["status"] == "OPEN"
    assert "fraude" in first_case["case_summary"].lower()
    assert "conclusión" in first_case["case_summary"].lower()

    detail_payload = client.get(f"/review-cases/{first_case['review_case_id']}").json()
    assert detail_payload["success"] is True
    assert len(detail_payload["data"]["score_components"]) >= 1
    assert all("points" in component for component in detail_payload["data"]["score_components"])


@pytest.mark.integration
def test_normal_sample_creates_no_review_cases():
    client = get_test_client()
    with Path("data/samples/sample_presidential_table_level.csv").open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_scoring_normal", "execution_mode": "EXPLORATORY"},
            files={"file": ("sample_scoring_normal.csv", fh, "text/csv")},
        )
    payload = response.json()
    assert payload["success"] is True
    ingestion_run_id = payload["data"]["ingestion_run_id"]

    assert client.post(f"/ingestions/{ingestion_run_id}/profile").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/map", json={}).json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/load-core").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/calculate-basic-metrics").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/generate-eda-alerts").json()["success"] is True

    score_payload = client.post(f"/ingestions/{ingestion_run_id}/calculate-scores").json()
    assert score_payload["success"] is True
    assert score_payload["data"]["review_cases_created"] == 0
