from datetime import datetime
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import CandidateLabel, DashboardReport
from gupiaofenxi.pipeline.scoring import score_candidate
from gupiaofenxi.pipeline.strong_pool import build_strong_pool


def _matches_base_filters(quote, settings: AppSettings, manual_exclusions: set[str]) -> bool:
    if quote.symbol in manual_exclusions:
        return False
    if quote.is_st or quote.is_suspended:
        return False
    if quote.close < settings.min_price or quote.close > settings.max_price:
        return False
    if quote.amount < settings.min_amount:
        return False
    return True


def build_dashboard_report(
    sample_dir: Path,
    settings: AppSettings,
    manual_exclusions: set[str],
    favorite_symbols: set[str] | None = None,
    symbol_query: str = "",
    name_query: str = "",
    provider=None,
) -> DashboardReport:
    favorite_symbols = favorite_symbols or set()
    symbol_query = symbol_query.strip()
    name_query = name_query.strip()
    provider = provider or SampleDataProvider(sample_dir)
    quotes, quote_status = provider.load_daily_quotes()
    market_temperature, index_status = provider.load_market_temperature()
    if symbol_query or name_query:
        pool = [
            quote
            for quote in quotes
            if _matches_base_filters(quote, settings, manual_exclusions)
        ]
        pool = [quote for quote in pool if symbol_query in quote.symbol]
        pool = [quote for quote in pool if name_query in quote.name]
        pool = sorted(pool, key=lambda quote: (-quote.amount, -quote.pct_change, quote.symbol))[
            : settings.top_pool_size
        ]
    else:
        pool = build_strong_pool(quotes, settings, manual_exclusions)
    candidates = sorted(
        [
            score_candidate(quote, settings).model_copy(
                update={"is_favorite": quote.symbol in favorite_symbols}
            )
            for quote in pool
        ],
        key=lambda item: item.score,
        reverse=True,
    )
    favorite_candidates = sorted(
        [
            score_candidate(quote, settings).model_copy(update={"is_favorite": True})
            for quote in quotes
            if quote.symbol in favorite_symbols and quote.symbol not in manual_exclusions
        ],
        key=lambda item: item.score,
        reverse=True,
    )
    high_score_count = sum(1 for item in candidates if item.label == CandidateLabel.STRONG_WATCH)
    risk_count = sum(1 for item in candidates if item.label == CandidateLabel.HIGH_RISK)
    report_date = max((quote.trade_date for quote in quotes), default=datetime.now().date())
    return DashboardReport(
        report_date=report_date,
        generated_at=datetime.now(),
        market_temperature=market_temperature,
        strong_pool_count=len(pool),
        high_score_count=high_score_count,
        risk_count=risk_count,
        price_range=(settings.min_price, settings.max_price),
        data_status=[*quote_status.records, *index_status.records],
        candidates=candidates,
        favorite_candidates=favorite_candidates,
    )
