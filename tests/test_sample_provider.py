from pathlib import Path

from gupiaofenxi.data.sample_provider import SampleDataProvider


def test_sample_provider_loads_quotes_and_records_status():
    provider = SampleDataProvider(Path("data/sample"))

    quotes, status_log = provider.load_daily_quotes()

    assert len(quotes) == 6
    assert quotes[0].symbol == "000001"
    assert status_log.latest("日线行情").success_count == 6


def test_sample_provider_loads_market_temperature():
    provider = SampleDataProvider(Path("data/sample"))

    temperature, status_log = provider.load_market_temperature()

    assert temperature == "偏强"
    assert status_log.latest("指数数据").message == "获取成功"
