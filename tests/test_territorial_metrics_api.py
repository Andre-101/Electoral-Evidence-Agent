from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_loaded_core(client, sample_path: Path, upload_name: str) -> str:
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_territorial_metrics", "execution_mode": "EXPLORATORY"},
            files={"file": (upload_name, fh, "text/csv")},
        )
    payload = response.json()
    assert payload["success"] is True
    ingestion_run_id = payload["data"]["ingestion_run_id"]

    assert client.post(f"/ingestions/{ingestion_run_id}/profile").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/map", json={}).json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/load-core").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/calculate-basic-metrics").json()["success"] is True
    return ingestion_run_id


@pytest.mark.integration
def test_calculate_territorial_metrics_and_alerts():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_territorial_outlier.csv"),
        "sample_territorial_outlier.csv",
    )

    territorial_payload = client.post(f"/ingestions/{ingestion_run_id}/calculate-territorial-metrics").json()
    assert territorial_payload["success"] is True
    assert territorial_payload["data"]["station_metrics_created"] >= 1
    assert territorial_payload["data"]["municipality_metrics_created"] >= 1
    assert territorial_payload["data"]["option_table_metrics_updated"] == 12

    station_payload = client.get(f"/ingestions/{ingestion_run_id}/station-metrics").json()
    assert station_payload["success"] is True
    assert station_payload["data"]["total"] >= 1
    assert station_payload["data"]["items"][0]["total_tables"] == 6
    assert station_payload["data"]["items"][0]["turnout_mad"] is not None

    option_payload = client.get(f"/ingestions/{ingestion_run_id}/option-table-metrics").json()
    assert option_payload["success"] is True
    assert option_payload["data"]["total"] == 12
    assert any(
        item["robust_z_vs_station"] is not None and abs(item["robust_z_vs_station"]) >= 3.5
        for item in option_payload["data"]["items"]
    )
    assert any(
        item["diff_vs_station"] is not None and item["diff_vs_station"] >= 0.30
        for item in option_payload["data"]["items"]
    )

    alert_payload = client.post(f"/ingestions/{ingestion_run_id}/generate-eda-alerts").json()
    assert alert_payload["success"] is True

    summary_payload = client.get(f"/ingestions/{ingestion_run_id}/eda-summary").json()
    assert summary_payload["success"] is True
    by_code = summary_payload["data"]["by_alert_code"]

    assert by_code["TABLE_TURNOUT_OUTLIER_STATION"] >= 1
    assert by_code["TABLE_PARTY_SHARE_OUTLIER_STATION"] >= 1
    assert by_code["TABLE_DIFF_STATION_GE_30PP"] >= 1
