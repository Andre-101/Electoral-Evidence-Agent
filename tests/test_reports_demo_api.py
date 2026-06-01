from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_case_with_dossier(client) -> tuple[str, str]:
    demo_payload = client.post("/demo/run").json()
    assert demo_payload["success"] is True
    assert demo_payload["data"]["review_cases_created"] >= 1
    return demo_payload["data"]["ingestion_run_id"], demo_payload["data"]["first_review_case_id"]


@pytest.mark.integration
def test_demo_pipeline_generates_reports():
    client = get_test_client()
    demo_payload = client.post("/demo/run").json()

    assert demo_payload["success"] is True
    data = demo_payload["data"]
    assert data["review_cases_created"] >= 1
    assert Path(data["case_report_path"]).exists()
    assert Path(data["executive_report_path"]).exists()

    case_report = client.get(f"/reports/{data['case_report_id']}").json()
    assert case_report["success"] is True
    assert case_report["data"]["report_type"] == "CASE"

    html_response = client.get(f"/reports/{data['case_report_id']}/html")
    assert html_response.status_code == 200
    assert "Reporte de caso de revisión" in html_response.text
    assert "No concluye fraude electoral" in html_response.text


@pytest.mark.integration
def test_generate_case_report_endpoint():
    client = get_test_client()
    _, review_case_id = _prepare_case_with_dossier(client)

    report_payload = client.post(f"/reports/case/{review_case_id}").json()
    assert report_payload["success"] is True
    assert report_payload["data"]["report_type"] == "CASE"
    assert report_payload["data"]["export"]["export_format"] == "HTML"
    assert Path(report_payload["data"]["export"]["file_path"]).exists()


@pytest.mark.integration
def test_generate_executive_report_endpoint():
    client = get_test_client()
    ingestion_run_id, _ = _prepare_case_with_dossier(client)

    report_payload = client.post(f"/reports/executive/{ingestion_run_id}").json()
    assert report_payload["success"] is True
    assert report_payload["data"]["report_type"] == "EXECUTIVE"
    assert Path(report_payload["data"]["export"]["file_path"]).exists()
