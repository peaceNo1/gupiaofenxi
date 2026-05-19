from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, CandidateScore, StockQuote
from gupiaofenxi.pipeline.historical_prediction import PredictionEstimate
from gupiaofenxi.pipeline.trade_plan import build_trade_plan


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_candidate(
    quote: StockQuote,
    settings: AppSettings,
    prediction_estimate: PredictionEstimate | None = None,
) -> CandidateScore:
    if quote.close < settings.min_price or quote.close > settings.max_price:
        return CandidateScore(
            symbol=quote.symbol,
            name=quote.name,
            current_price=quote.close,
            daily_pct_change=quote.pct_change,
            score=0,
            next_day_up_probability=0,
            three_day_up_probability=0,
            expected_return=0,
            label=CandidateLabel.PRICE_MISMATCH,
            reason="当前价格不在个人可接受价格范围内",
            strength_score=0,
            dip_position_score=0,
            sentiment_score=0,
            historical_similarity_score=0,
            trade_plan=None,
        )

    strength_score = _clamp(50 + quote.pct_change * 4, 0, 100)
    dip_position_score = _clamp(80 - abs(quote.pct_change) * 3, 0, 100)
    sentiment_score = _clamp(quote.amount / settings.min_amount * 30, 0, 100)
    historical_similarity_score = _clamp((strength_score + dip_position_score) / 2, 0, 100)
    score = round(
        strength_score * 0.3
        + dip_position_score * 0.3
        + sentiment_score * 0.2
        + historical_similarity_score * 0.2,
        2,
    )

    if score >= settings.high_score_threshold:
        label = CandidateLabel.STRONG_WATCH
    elif score >= 55:
        label = CandidateLabel.WATCH
    else:
        label = CandidateLabel.REJECT
    if prediction_estimate is None:
        prediction_estimate = PredictionEstimate(
            next_day_up_probability=round(_clamp(0.42 + score / 500, 0, 0.78), 4),
            three_day_up_probability=round(_clamp(0.45 + score / 450, 0, 0.82), 4),
            expected_return=round((score - 50) / 10, 2),
            sample_count=0,
            source="fallback",
        )
    if prediction_estimate.source == "history":
        reason = f"基于{prediction_estimate.sample_count}个历史相似样本统计，结合强弱、回踩位置和成交额"
    else:
        reason = "历史样本不足，暂按综合分估算，结合强弱、回踩位置和成交额"

    return CandidateScore(
        symbol=quote.symbol,
        name=quote.name,
        current_price=quote.close,
        daily_pct_change=quote.pct_change,
        score=score,
        next_day_up_probability=prediction_estimate.next_day_up_probability,
        three_day_up_probability=prediction_estimate.three_day_up_probability,
        expected_return=prediction_estimate.expected_return,
        label=label,
        reason=reason,
        strength_score=round(strength_score, 2),
        dip_position_score=round(dip_position_score, 2),
        sentiment_score=round(sentiment_score, 2),
        historical_similarity_score=round(historical_similarity_score, 2),
        trade_plan=build_trade_plan(quote),
    )
