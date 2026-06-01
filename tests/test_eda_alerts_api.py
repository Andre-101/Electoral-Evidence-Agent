from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_loaded_core(client, sample_path: Path, upload_name: str) -> str:
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_eda_alerts", "execution_mode": "EXPLORATORY"},
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
def test_generate_eda_alerts_from_anomaly_sample():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_eda_anomalies.csv"),
        "sample_eda_anomalies.csv",
    )

    generate_payload = client.post(f"/ingestions/{ingestion_run_id}/generate-eda-alerts").json()
    assert generate_payload["success"] is True
    assert generate_payload["data"]["eda_alerts_created"] >= 4

    summary_payload = client.get(f"/ingestions/{ingestion_run_id}/eda-summary").json()
    assert summary_payload["success"] is True

    by_code = summary_payload["data"]["by_alert_code"]
    assert by_code["TURNOUT_GE_95"] >= 1
    assert by_code["TURNOUT_LE_20"] >= 1
    assert by_code["TURNOUT_GT_100"] >= 1
    assert by_code["WINNER_SHARE_GE_95"] >= 1
    assert by_code["MARGIN_GE_80"] >= 1

    alerts_payload = client.get(f"/ingestions/{ingestion_run_id}/eda-alerts").json()
    assert alerts_payload["success"] is True
    assert alerts_payload["data"]["total"] == summary_payload["data"]["eda_alerts_count"]
    assert all("fraude" not in item["message"].lower() for item in alerts_payload["data"]["items"])


@pytest.mark.integration
def test_generate_eda_alerts_from_normal_sample_has_limited_alerts():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_presidential_table_level.csv"),
        "sample_normal_eda.csv",
    )

    generate_payload = client.post(f"/ingestions/{ingestion_run_id}/generate-eda-alerts").json()
    assert generate_payload["success"] is True

    summary_payload = client.get(f"/ingestions/{ingestion_run_id}/eda-summary").json()
    assert summary_payload["success"] is True
    assert summary_payload["data"]["eda_alerts_count"] == 0
