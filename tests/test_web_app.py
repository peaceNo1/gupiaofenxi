from pathlib import Path

from fastapi.testclient import TestClient

from gupiaofenxi.data.csv_provider import CsvDataProvider
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import ManualOverride
from gupiaofenxi.storage.json_store import JsonStore
from gupiaofenxi.web.app import create_app


class FakeRefresher:
    def __init__(self, count=1, error=None):
        self.count = count
        self.error = error
        self.called = False

    def refresh(self):
        self.called = True
        if self.error:
            raise self.error
        return self.count


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


def test_refresh_button_calls_eastmoney_refresher(tmp_path):
    refresher = FakeRefresher(count=123)
    client = TestClient(
        create_app(
            store_root=tmp_path,
            provider_factory=sample_provider_factory,
            refresher=refresher,
        )
    )

    response = client.post("/refresh?min_price=20&max_price=30", follow_redirects=False)

    assert refresher.called is True
    assert response.status_code == 303
    assert "refresh_status=" in response.headers["location"]
    assert "min_price=20" in response.headers["location"]


def test_refresh_url_also_works_with_get(tmp_path):
    refresher = FakeRefresher(count=456)
    client = TestClient(
        create_app(
            store_root=tmp_path,
            provider_factory=sample_provider_factory,
            refresher=refresher,
        )
    )

    response = client.get("/refresh?min_price=3&max_price=60", follow_redirects=False)

    assert refresher.called is True
    assert response.status_code == 303
    assert "refresh_status=" in response.headers["location"]


def test_refresh_failure_uses_friendly_message_without_raw_network_error(tmp_path):
    refresher = FakeRefresher(error=ConnectionError("RemoteDisconnected raw detail"))
    client = TestClient(
        create_app(
            store_root=tmp_path,
            provider_factory=sample_provider_factory,
            refresher=refresher,
        )
    )

    response = client.get("/refresh?min_price=3&max_price=60", follow_redirects=False)

    assert refresher.called is True
    assert response.status_code == 303
    location = response.headers["location"]
    assert "refresh_error=" in location
    assert "RemoteDisconnected" not in location


def test_refresh_button_is_rendered(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/")

    assert response.status_code == 200
    assert "立即刷新东方财富数据" in response.text
    assert "/api/watch/refresh" in response.text


def test_dashboard_renders_watch_mode_and_daily_change_column(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/?min_price=3&max_price=13")

    assert response.status_code == 200
    assert "实时盯盘" in response.text
    assert "当日涨幅" in response.text
    assert 'data-watch-refresh="3"' in response.text
    assert "后台盯盘中，数据自动更新" in response.text
    assert "/refresh?min_price={{" not in response.text


def test_dashboard_uses_background_watch_without_page_navigation(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/?min_price=3&max_price=13")

    assert response.status_code == 200
    assert "/api/watch/events" in response.text
    assert "/api/watch/refresh" in response.text
    assert "new EventSource" in response.text
    assert "window.location.href" not in response.text
    assert '<tbody id="candidate-rows">' in response.text
    assert "renderReport" in response.text


def test_watch_refresh_api_updates_without_redirect(tmp_path):
    refresher = FakeRefresher(count=7)
    client = TestClient(
        create_app(
            store_root=tmp_path,
            provider_factory=sample_provider_factory,
            refresher=refresher,
        )
    )

    response = client.post("/api/watch/refresh?min_price=3&max_price=13")

    assert refresher.called is True
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["refreshed_count"] == 7
    assert payload["report"]["candidates"]


def test_dashboard_supports_symbol_name_search_and_favorite_space(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    add_response = client.post("/api/favorites/000001")
    response = client.get("/?symbol_query=000&name_query=银行")

    assert add_response.status_code == 200
    assert response.status_code == 200
    assert 'name="symbol_query"' in response.text
    assert 'value="000"' in response.text
    assert 'name="name_query"' in response.text
    assert 'value="银行"' in response.text
    assert "自选空间" in response.text
    assert "000001" in response.text
    assert "移出自选" in response.text


def test_favorite_api_toggles_focus_symbol(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    add_response = client.post("/api/favorites/000001")
    delete_response = client.delete("/api/favorites/000001")

    assert add_response.status_code == 200
    assert add_response.json()["favorites"] == ["000001"]
    assert delete_response.status_code == 200
    assert delete_response.json()["favorites"] == []
