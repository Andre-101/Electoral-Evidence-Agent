from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_loaded_core(client, sample_path: Path, upload_name: str) -> str:
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_quality_totals", "execution_mode": "EXPLORATORY"},
            files={"file": (upload_name, fh, "text/csv")},
        )
    payload = response.json()
    assert payload["success"] is True
    ingestion_run_id = payload["data"]["ingestion_run_id"]

    assert client.post(f"/ingestions/{ingestion_run_id}/profile").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/map", json={}).json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/load-core").json()["success"] is True
    return ingestion_run_id


@pytest.mark.integration
def test_calculate_table_totals_valid_sample():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_presidential_table_level.csv"),
        "sample_totals.csv",
    )

    totals_payload = client.post(f"/ingestions/{ingestion_run_id}/calculate-totals").json()
    assert totals_payload["success"] is True
    assert totals_payload["data"]["table_totals_created"] == 3

    query_payload = client.get(f"/ingestions/{ingestion_run_id}/table-totals").json()
    assert query_payload["success"] is True
    assert query_payload["data"]["total"] == 3

    total_votes = sorted(item["total_votes"] for item in query_payload["data"]["items"])
    assert total_votes == [220, 220, 223]


@pytest.mark.integration
def test_quality_validation_votes_greater_than_census():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_quality_invalid.csv"),
        "sample_quality_invalid.csv",
    )

    quality_payload = client.post(f"/ingestions/{ingestion_run_id}/validate-quality").json()
    assert quality_payload["success"] is True
    assert quality_payload["data"]["quality_alerts_created"] >= 1
    assert quality_payload["data"]["critical_alerts"] >= 1

    summary_payload = client.get(f"/ingestions/{ingestion_run_id}/quality-summary").json()
    assert summary_payload["success"] is True
    assert summary_payload["data"]["by_alert_code"]["VOTES_GREATER_THAN_CENSUS"] >= 1
