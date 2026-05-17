import sys
from datetime import date
from pathlib import Path

import pandas as pd

from gupiaofenxi.data.akshare_provider import AkshareDataProvider
from gupiaofenxi.data.hybrid_provider import HybridDataProvider
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import DataTaskStatus


class FakeAkshare:
    @staticmethod
    def stock_zh_a_spot_em():
        return pd.DataFrame(
            [
                {
                    "代码": "000001",
                    "名称": "平安银行",
                    "最新价": 10.99,
                    "今开": 11.05,
                    "最高": 11.14,
                    "最低": 10.96,
                    "成交量": 974700,
                    "成交额": 107000000,
                    "涨跌幅": -0.54,
                },
                {
                    "代码": "600000",
                    "名称": "浦发银行",
                    "最新价": 9.07,
                    "今开": 9.01,
                    "最高": 9.10,
                    "最低": 8.96,
                    "成交量": 1000000,
                    "成交额": 120000000,
                    "涨跌幅": 0.55,
                },
            ]
        )


class FailingProvider:
    source_name = "failing"

    def load_daily_quotes(self):
        raise RuntimeError("network down")

    def load_market_temperature(self):
        raise RuntimeError("network down")


def test_akshare_provider_maps_realtime_spot_quotes(monkeypatch):
    monkeypatch.setitem(sys.modules, "akshare", FakeAkshare)

    quotes, status = AkshareDataProvider().load_daily_quotes()

    assert quotes[0].symbol == "000001"
    assert quotes[0].name == "平安银行"
    assert quotes[0].close == 10.99
    assert quotes[0].trade_date == date.today()
    assert status.latest("实时行情").status == DataTaskStatus.SUCCESS


def test_akshare_provider_computes_market_temperature(monkeypatch):
    monkeypatch.setitem(sys.modules, "akshare", FakeAkshare)

    temperature, status = AkshareDataProvider().load_market_temperature()

    assert temperature == "震荡"
    assert status.latest("市场温度").success_count == 2


def test_hybrid_provider_falls_back_to_sample_data():
    provider = HybridDataProvider(
        primary=FailingProvider(),
        fallback=SampleDataProvider(Path("data/sample")),
    )

    quotes, status = provider.load_daily_quotes()

    assert quotes
    assert status.records[0].status == DataTaskStatus.FAILED
    assert status.records[0].used_cache is True
    assert status.records[-1].source_name == "sample"
