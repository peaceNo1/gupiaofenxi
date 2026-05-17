from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.pipeline.strong_pool import build_strong_pool


def test_strong_pool_excludes_prices_outside_range():
    quotes, _ = SampleDataProvider(Path("data/sample")).load_daily_quotes()

    pool = build_strong_pool(
        quotes, AppSettings(min_price=3, max_price=60), manual_exclusions=set()
    )
    symbols = {item.symbol for item in pool}

    assert "600519" not in symbols
    assert "600001" not in symbols
    assert "002001" in symbols


def test_strong_pool_honors_manual_exclusions():
    quotes, _ = SampleDataProvider(Path("data/sample")).load_daily_quotes()

    pool = build_strong_pool(quotes, AppSettings(), manual_exclusions={"002001"})
    symbols = {item.symbol for item in pool}

    assert "002001" not in symbols
