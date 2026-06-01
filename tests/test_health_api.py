from tests.conftest import get_test_client


def test_version_endpoint():
    client = get_test_client()
    response = client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["pipeline_version"] == "0.1.0"
