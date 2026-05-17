from pathlib import Path

from fastapi.testclient import TestClient

from gupiaofenxi.data.csv_provider import CsvDataProvider
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import ManualOverride
from gupiaofenxi.storage.json_store import JsonStore
from gupiaofenxi.web.app import create_app


def sample_provider_factory():
    return SampleDataProvider(Path("data/sample"))


def test_dashboard_page_renders_ranking_first_view(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/")

    assert response.status_code == 200
    assert "<table>" in response.text
    assert "002001" in response.text
    assert "10.50" in response.text


def test_api_report_respects_price_query_range_and_saves_report(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

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
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

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


def test_dashboard_can_use_exported_csv_provider(tmp_path):
    csv_path = tmp_path / "daily_quotes.csv"
    csv_path.write_text(
        "代码,名称,最新价,今开,最高,最低,成交量,成交额,涨跌幅\n"
        "000001,平安银行,10.99,11.05,11.14,10.96,974700,107000000,-0.54\n",
        encoding="utf-8-sig",
    )
    client = TestClient(
        create_app(
            store_root=tmp_path / "store",
            provider_factory=lambda: CsvDataProvider(csv_path),
        )
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "000001" in response.text
    assert "10.99" in response.text
