import csv

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
