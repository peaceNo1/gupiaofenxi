from datetime import datetime
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import CandidateLabel, DashboardReport
from gupiaofenxi.pipeline.scoring import score_candidate
from gupiaofenxi.pipeline.strong_pool import build_strong_pool


def build_dashboard_report(
    sample_dir: Path,
    settings: AppSettings,
    manual_exclusions: set[str],
    provider=None,
) -> DashboardReport:
    provider = provider or SampleDataProvider(sample_dir)
    quotes, quote_status = provider.load_daily_quotes()
    market_temperature, index_status = provider.load_market_temperature()
    pool = build_strong_pool(quotes, settings, manual_exclusions)
    candidates = sorted(
        [score_candidate(quote, settings) for quote in pool],
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
    )
