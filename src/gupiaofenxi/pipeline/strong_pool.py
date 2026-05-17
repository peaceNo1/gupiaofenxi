from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import StockQuote


def build_strong_pool(
    quotes: list[StockQuote],
    settings: AppSettings,
    manual_exclusions: set[str],
) -> list[StockQuote]:
    filtered = []
    for quote in quotes:
        if quote.symbol in manual_exclusions:
            continue
        if quote.is_st or quote.is_suspended:
            continue
        if quote.close < settings.min_price or quote.close > settings.max_price:
            continue
        if quote.amount < settings.min_amount:
            continue
        filtered.append(quote)

    return sorted(filtered, key=lambda quote: (-quote.amount, -quote.pct_change, quote.symbol))[
        : settings.top_pool_size
    ]
