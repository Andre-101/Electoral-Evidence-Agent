from pathlib import Path

import pytest

from tests.conftest import get_test_client


def _prepare_loaded_core(client, sample_path: Path, upload_name: str) -> str:
    with sample_path.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_basic_metrics", "execution_mode": "EXPLORATORY"},
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
def test_calculate_basic_metrics_flow():
    client = get_test_client()
    ingestion_run_id = _prepare_loaded_core(
        client,
        Path("data/samples/sample_presidential_table_level.csv"),
        "sample_basic_metrics.csv",
    )

    metrics_payload = client.post(f"/ingestions/{ingestion_run_id}/calculate-basic-metrics").json()
    assert metrics_payload["success"] is True
    assert metrics_payload["data"]["table_totals_created"] == 3
    assert metrics_payload["data"]["table_metrics_created"] == 3
    assert metrics_payload["data"]["option_table_metrics_created"] == 7

    table_metrics = client.get(f"/ingestions/{ingestion_run_id}/table-metrics").json()
    assert table_metrics["success"] is True
    assert table_metrics["data"]["total"] == 3

    items = table_metrics["data"]["items"]
    winner_votes = sorted(item["winner_votes"] for item in items)
    assert winner_votes == [120, 130, 140]

    # Table COLEGIO A / MESA 1 has total 223, registered voters 400.
    # turnout ~= 0.5575 and winner_share = 120 / 215 ~= 0.558139.
    assert any(abs(item["turnout"] - 0.5575) < 0.0001 for item in items)
    assert any(abs(item["winner_share"] - (120 / 215)) < 0.0001 for item in items)

    option_metrics = client.get(f"/ingestions/{ingestion_run_id}/option-table-metrics").json()
    assert option_metrics["success"] is True
    assert option_metrics["data"]["total"] == 7
    assert all("vote_share" in item for item in option_metrics["data"]["items"])
