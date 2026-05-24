from datetime import datetime
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import AlertItem, CandidateLabel, DashboardReport, Position, PositionSnapshot, StockQuote
from gupiaofenxi.pipeline.historical_prediction import HistoricalPrediction, SimilaritySample
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


def _score_with_history(quote, settings: AppSettings, predictor: HistoricalPrediction):
    base = score_candidate(quote, settings)
    return score_candidate(
        quote,
        settings,
        prediction_estimate=predictor.estimate(base.score),
    )


def _position_status(profit_pct: float) -> str:
    if profit_pct <= -5:
        return "止损"
    if profit_pct >= 8:
        return "止盈"
    return "持有"


def _build_positions(
    quotes: list[StockQuote],
    positions: list[Position],
) -> list[PositionSnapshot]:
    quote_by_symbol = {quote.symbol: quote for quote in quotes}
    snapshots: list[PositionSnapshot] = []
    for position in positions:
        quote = quote_by_symbol.get(position.symbol)
        current_price = quote.close if quote else position.cost_price
        name = position.name or (quote.name if quote else position.symbol)
        market_value = round(current_price * position.quantity, 2)
        cost_value = position.cost_price * position.quantity
        profit = round(market_value - cost_value, 2)
        profit_pct = round((profit / cost_value * 100) if cost_value else 0, 2)
        snapshots.append(
            PositionSnapshot(
                symbol=position.symbol,
                name=name,
                cost_price=position.cost_price,
                quantity=position.quantity,
                current_price=current_price,
                market_value=market_value,
                profit=profit,
                profit_pct=profit_pct,
                status=_position_status(profit_pct),
            )
        )
    return snapshots


def _build_alerts(
    favorite_candidates,
    positions: list[PositionSnapshot],
) -> list[AlertItem]:
    alerts: list[AlertItem] = []
    for position in positions:
        if position.status in {"止损", "止盈"}:
            alerts.append(
                AlertItem(
                    symbol=position.symbol,
                    name=position.name,
                    level=position.status,
                    message=f"持仓{position.status}触发，收益率 {position.profit_pct:.2f}%",
                )
            )
    for item in favorite_candidates:
        plan = item.trade_plan
        if item.daily_pct_change >= 9.5:
            alerts.append(
                AlertItem(
                    symbol=item.symbol,
                    name=item.name,
                    level="涨停关注",
                    message=f"{item.name} 当日涨幅 {item.daily_pct_change:.2f}%，注意封板/炸板",
                )
            )
        if not plan:
            continue
        if plan.buy_low <= item.current_price <= plan.buy_high:
            alerts.append(
                AlertItem(
                    symbol=item.symbol,
                    name=item.name,
                    level="低吸区间",
                    message=f"{item.name} 到达低吸区间 {plan.buy_low}-{plan.buy_high}",
                )
            )
        if item.current_price <= plan.stop_loss:
            alerts.append(
                AlertItem(
                    symbol=item.symbol,
                    name=item.name,
                    level="止损",
                    message=f"{item.name} 跌破止损价 {plan.stop_loss}",
                )
            )
        if item.current_price >= plan.target_price:
            alerts.append(
                AlertItem(
                    symbol=item.symbol,
                    name=item.name,
                    level="目标价",
                    message=f"{item.name} 到达目标价 {plan.target_price}",
                )
            )
    return alerts


def build_dashboard_report(
    sample_dir: Path,
    settings: AppSettings,
    manual_exclusions: set[str],
    favorite_symbols: set[str] | None = None,
    symbol_query: str = "",
    name_query: str = "",
    prediction_samples: list[SimilaritySample | dict] | None = None,
    prediction_min_samples: int = 8,
    positions: list[Position] | None = None,
    provider=None,
) -> DashboardReport:
    favorite_symbols = favorite_symbols or set()
    symbol_query = symbol_query.strip()
    name_query = name_query.strip()
    provider = provider or SampleDataProvider(sample_dir)
    samples = [
        sample
        if isinstance(sample, SimilaritySample)
        else SimilaritySample(**sample)
        for sample in (prediction_samples or [])
    ]
    predictor = HistoricalPrediction(samples=samples, min_samples=prediction_min_samples)
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
            _score_with_history(quote, settings, predictor).model_copy(
                update={"is_favorite": quote.symbol in favorite_symbols}
            )
            for quote in pool
        ],
        key=lambda item: item.score,
        reverse=True,
    )
    favorite_candidates = sorted(
        [
            _score_with_history(quote, settings, predictor).model_copy(
                update={"is_favorite": True}
            )
            for quote in quotes
            if quote.symbol in favorite_symbols and quote.symbol not in manual_exclusions
        ],
        key=lambda item: item.score,
        reverse=True,
    )
    position_snapshots = _build_positions(quotes, positions or [])
    alerts = _build_alerts(favorite_candidates, position_snapshots)
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
        positions=position_snapshots,
        alerts=alerts,
    )
