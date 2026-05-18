from pathlib import Path

from gupiaofenxi.data.fallback_provider import FallbackDataProvider
from gupiaofenxi.data.sample_provider import SampleDataProvider


class EmptyProvider:
    def load_daily_quotes(self):
        return [], self.load_market_temperature()[1]

    def load_market_temperature(self):
        return "未知", SampleDataProvider(Path("data/sample")).load_market_temperature()[1]


def test_fallback_provider_uses_backup_when_primary_has_no_quotes():
    provider = FallbackDataProvider(
        primary=EmptyProvider(),
        fallback=SampleDataProvider(Path("data/sample")),
    )

    quotes, status = provider.load_daily_quotes()
    temperature, temperature_status = provider.load_market_temperature()

    assert quotes
    assert quotes[0].symbol == "000001"
    assert temperature == "偏强"
    assert status.records[-1].used_cache is True
    assert temperature_status.records[-1].used_cache is True
