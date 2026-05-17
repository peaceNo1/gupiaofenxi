from datetime import date

import pytest
from pydantic import ValidationError

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, StockQuote


def test_default_price_range_matches_personal_constraints():
    settings = AppSettings()

    assert settings.min_price == 3
    assert settings.max_price == 60


def test_app_settings_rejects_zero_min_amount():
    with pytest.raises(ValidationError):
        AppSettings(min_amount=0)


def test_stock_quote_computes_amplitude():
    quote = StockQuote(
        symbol="000001",
        name="平安银行",
        trade_date=date(2026, 5, 15),
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000000,
        amount=10500000,
        pct_change=3.5,
        is_st=False,
        is_suspended=False,
    )

    assert quote.amplitude == 20
    assert CandidateLabel.STRONG_WATCH.value == "强烈关注"


def test_stock_quote_rejects_zero_open_price():
    with pytest.raises(ValidationError):
        StockQuote(
            symbol="000001",
            name="平安银行",
            trade_date=date(2026, 5, 15),
            open=0,
            high=11,
            low=9,
            close=10.5,
            volume=1000000,
            amount=10500000,
            pct_change=3.5,
            is_st=False,
            is_suspended=False,
        )
