from fastapi.testclient import TestClient

from gupiaofenxi.domain.models import ManualOverride
from gupiaofenxi.storage.json_store import JsonStore
from gupiaofenxi.web.app import create_app


def test_dashboard_page_renders_ranking_first_view(tmp_path):
    client = TestClient(create_app(store_root=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "<table>" in response.text
    assert "002001" in response.text
    assert "10.50" in response.text


def test_api_report_respects_price_query_range_and_saves_report(tmp_path):
    client = TestClient(create_app(store_root=tmp_path))

    response = client.get("/api/report?min_price=20&max_price=30")

    assert response.status_code == 200
    payload = response.json()
    symbols = {item["symbol"] for item in payload["candidates"]}
    assert "002001" in symbols
    assert "000001" not in symbols
    assert "300001" not in symbols
    assert payload["price_range"] == [20.0, 30.0]
    assert list(tmp_path.glob("report-*.json"))


def test_dashboard_respects_price_query_and_manual_exclusions(tmp_path):
    JsonStore(tmp_path).save_manual_overrides(
        [ManualOverride(symbol="002001", excluded=True, note="manual skip")]
    )
    client = TestClient(create_app(store_root=tmp_path))

    response = client.get("/?min_price=20&max_price=30")

    assert response.status_code == 200
    assert "20.0-30.0" in response.text
    assert 'name="min_price"' in response.text
    assert 'value="20.0"' in response.text
    assert 'name="max_price"' in response.text
    assert 'value="30.0"' in response.text
    assert "002001" not in response.text
    assert "000001" not in response.text
    assert "300001" not in response.text
