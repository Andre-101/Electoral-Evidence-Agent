from tests.conftest import get_test_client


def test_human_readable_demo_report_does_not_fail():
    client = get_test_client()
    payload = client.post("/demo/run").json()
    assert payload["success"] is True
    report_id = payload["data"]["case_report_id"]

    html = client.get(f"/reports/{report_id}/html")
    assert html.status_code == 200
    assert "Información del caso" in html.text
    assert "Ver trazabilidad técnica del caso" in html.text
