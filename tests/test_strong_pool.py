from datetime import date
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import StockQuote
from gupiaofenxi.pipeline.strong_pool import build_strong_pool


def make_quote(
    symbol: str, amount: float = 200_000_000, pct_change: float = 5
) -> StockQuote:
    return StockQuote(
        symbol=symbol,
        name=symbol,
        trade_date=date(2026, 5, 17),
        open=10,
        high=11,
        low=9,
        close=10,
        volume=1_000_000,
        amount=amount,
        pct_change=pct_change,
    )


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


def test_strong_pool_ties_are_ordered_by_symbol():
    quotes = [
        make_quote("600002"),
        make_quote("600001"),
    ]

    pool = build_strong_pool(
        quotes,
        AppSettings(top_pool_size=1),
        manual_exclusions=set(),
    )

    assert [item.symbol for item in pool] == ["600001"]
