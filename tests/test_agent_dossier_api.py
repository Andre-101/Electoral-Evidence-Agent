from pathlib import Path

import pytest

from tests.conftest import get_test_client


FORBIDDEN_PHRASES = [
    "fraude confirmado",
    "culpable",
    "manipulación demostrada",
    "robo electoral",
    "prueba definitiva",
    "resultado falso",
    "se comprobó fraude",
    "fraude electoral demostrado",
]


def _prepare_review_case(client) -> str:
    sample_path = Path("data/samples/sample_territorial_outlier.csv")
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_dossier", "execution_mode": "EXPLORATORY"},
            files={"file": ("sample_dossier_territorial.csv", fh, "text/csv")},
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
    review_case_id = cases_payload["data"]["items"][0]["review_case_id"]
    assert client.post(f"/review-cases/{review_case_id}/evidence-items/generate").json()["success"] is True
    return review_case_id


@pytest.mark.integration
def test_generate_deterministic_dossier():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    dossier_payload = client.post(f"/review-cases/{review_case_id}/dossier?force_regenerate=true&use_llm=false").json()
    assert dossier_payload["success"] is True
    assert dossier_payload["data"]["dossier_status"] == "GENERATED"
    assert dossier_payload["data"]["language_policy_status"] == "PASSED"

    data = dossier_payload["data"]
    assert data["executive_summary"]
    assert "no se concluye fraude electoral" in data["executive_summary"].lower()
    assert "revisión humana" in data["executive_summary"].lower()
    assert "score" in data["technical_summary"].lower()
    assert "actas" in data["recommended_next_steps"].lower()

    all_text = "\n".join([
        data["executive_summary"],
        data["technical_summary"],
        data["limitations"],
        data["recommended_next_steps"],
    ]).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in all_text


@pytest.mark.integration
def test_get_existing_dossier():
    client = get_test_client()
    review_case_id = _prepare_review_case(client)

    created = client.post(f"/review-cases/{review_case_id}/dossier?force_regenerate=true&use_llm=false").json()
    assert created["success"] is True

    retrieved = client.get(f"/review-cases/{review_case_id}/dossier").json()
    assert retrieved["success"] is True
    assert retrieved["data"]["review_case_id"] == review_case_id
    assert retrieved["data"]["evidence_dossier_id"] == created["data"]["evidence_dossier_id"]
