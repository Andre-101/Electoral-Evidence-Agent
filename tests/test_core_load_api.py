from pathlib import Path

import pytest

from tests.conftest import get_test_client


@pytest.mark.integration
def test_ingestion_to_core_load_flow():
    client = get_test_client()
    sample = Path("data/samples/sample_presidential_table_level.csv")

    with sample.open("rb") as fh:
        response = client.post(
            "/ingestions",
            data={"source_name": "test_core_load", "execution_mode": "EXPLORATORY"},
            files={"file": ("sample_core_load.csv", fh, "text/csv")},
        )
    payload = response.json()
    assert payload["success"] is True
    ingestion_run_id = payload["data"]["ingestion_run_id"]

    assert client.post(f"/ingestions/{ingestion_run_id}/profile").json()["success"] is True
    assert client.post(f"/ingestions/{ingestion_run_id}/map", json={}).json()["success"] is True

    load_payload = client.post(f"/ingestions/{ingestion_run_id}/load-core").json()
    assert load_payload["success"] is True
    assert load_payload["data"]["vote_results_upserted"] == 7
    assert load_payload["data"]["polling_tables_touched"] == 3
    assert load_payload["data"]["electoral_options_touched"] >= 3

    summary_payload = client.get(f"/ingestions/{ingestion_run_id}/core-summary").json()
    assert summary_payload["success"] is True
    assert summary_payload["data"]["vote_results"] == 7
