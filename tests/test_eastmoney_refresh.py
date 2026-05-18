import csv

import requests

from gupiaofenxi.data.eastmoney_refresh import EastmoneyRefresher


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "data": {
                "diff": [
                    {
                        "f12": "000001",
                        "f14": "平安银行",
                        "f2": 10.99,
                        "f17": 11.05,
                        "f15": 11.14,
                        "f16": 10.96,
                        "f5": 974700,
                        "f6": 107000000,
                        "f3": -0.54,
                    }
                ]
            }
        }


class FakeSession:
    trust_env = True

    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return FakeResponse()


class FlakySession:
    trust_env = True

    def __init__(self):
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if len(self.calls) == 1:
            raise requests.ConnectionError("RemoteDisconnected")
        return FakeResponse()


class StockFallbackSession:
    trust_env = True

    def __init__(self):
        self.calls = []

    def get(self, url, *args, **kwargs):
        self.calls.append((url, args, kwargs))
        if "clist/get" in url:
            raise requests.ConnectionError("RemoteDisconnected")
        return FakeStockResponse()


class FakeStockResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "data": {
                "f57": "000001",
                "f58": "平安银行",
                "f43": 1099,
                "f46": 1105,
                "f44": 1114,
                "f45": 1096,
                "f47": 974742,
                "f48": 1074648532.65,
                "f170": -54,
            }
        }


class PagedSession:
    trust_env = True

    def __init__(self):
        self.pages = []

    def get(self, *args, **kwargs):
        page = kwargs["params"]["pn"]
        self.pages.append(page)
        return PagedResponse(page)


class PagedResponse:
    def __init__(self, page):
        self.page = page

    def raise_for_status(self):
        return None

    def json(self):
        if self.page == 1:
            row = {"f12": "000001", "f14": "平安银行", "f2": 10.99}
        else:
            row = {"f12": "000002", "f14": "万科A", "f2": 8.40}
        return {"data": {"total": 2, "diff": [row]}}


def test_eastmoney_refresher_writes_import_csv(monkeypatch, tmp_path):
    fake_session = FakeSession()
    monkeypatch.setattr(
        "gupiaofenxi.data.eastmoney_refresh.requests.Session",
        lambda: fake_session,
    )
    csv_path = tmp_path / "daily_quotes.csv"

    count = EastmoneyRefresher(csv_path).refresh()

    assert count == 1
    assert fake_session.trust_env is False
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    assert rows[0]["代码"] == "000001"
    assert rows[0]["名称"] == "平安银行"
    assert rows[0]["最新价"] == "10.99"


def test_eastmoney_refresher_tries_backup_endpoint_after_disconnect(monkeypatch, tmp_path):
    fake_session = FlakySession()
    monkeypatch.setattr(
        "gupiaofenxi.data.eastmoney_refresh.requests.Session",
        lambda: fake_session,
    )
    csv_path = tmp_path / "daily_quotes.csv"

    count = EastmoneyRefresher(csv_path).refresh()

    assert count == 1
    assert len(fake_session.calls) == 2
    first_url = fake_session.calls[0][0][0]
    second_url = fake_session.calls[1][0][0]
    assert first_url != second_url


def test_eastmoney_refresher_falls_back_to_known_symbols(monkeypatch, tmp_path):
    fake_session = StockFallbackSession()
    monkeypatch.setattr(
        "gupiaofenxi.data.eastmoney_refresh.requests.Session",
        lambda: fake_session,
    )
    known_symbols = tmp_path / "known.csv"
    known_symbols.write_text("symbol,name\n000001,平安银行\n", encoding="utf-8-sig")
    csv_path = tmp_path / "daily_quotes.csv"

    count = EastmoneyRefresher(csv_path, symbols_csv_path=known_symbols).refresh()

    assert count == 1
    assert any("stock/get" in call[0] for call in fake_session.calls)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    assert rows[0]["代码"] == "000001"
    assert rows[0]["名称"] == "平安银行"
    assert rows[0]["最新价"] == "10.99"
    assert rows[0]["涨跌幅"] == "-0.54"


def test_eastmoney_refresher_fetches_all_pages(monkeypatch, tmp_path):
    fake_session = PagedSession()
    monkeypatch.setattr(
        "gupiaofenxi.data.eastmoney_refresh.requests.Session",
        lambda: fake_session,
    )
    csv_path = tmp_path / "daily_quotes.csv"

    count = EastmoneyRefresher(csv_path).refresh()

    assert count == 2
    assert fake_session.pages == [1, 2]
