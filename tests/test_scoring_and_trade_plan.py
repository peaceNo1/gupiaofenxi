from datetime import date

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, StockQuote
from gupiaofenxi.pipeline.scoring import score_candidate
from gupiaofenxi.pipeline.historical_prediction import PredictionEstimate


def make_quote(close=24.5, pct_change=2.1, amount=180000000):
    return StockQuote(
        symbol="002001",
        name="新和成",
        trade_date=date(2026, 5, 15),
        open=24,
        high=25.3,
        low=23.2,
        close=close,
        volume=900000,
        amount=amount,
        pct_change=pct_change,
        is_st=False,
        is_suspended=False,
        industry="医药",
        concept="合成生物",
    )


def test_score_candidate_returns_full_prediction_fields():
    candidate = score_candidate(make_quote(), AppSettings())

    assert candidate.symbol == "002001"
    assert candidate.daily_pct_change == 2.1
    assert 0 <= candidate.score <= 100
    assert 0 <= candidate.next_day_up_probability <= 1
    assert 0 <= candidate.three_day_up_probability <= 1
    assert candidate.trade_plan is not None
    assert candidate.trade_plan.stop_loss < candidate.trade_plan.buy_low


def test_score_candidate_marks_price_mismatch():
    candidate = score_candidate(make_quote(close=88), AppSettings(min_price=3, max_price=60))

    assert candidate.label == CandidateLabel.PRICE_MISMATCH
    assert candidate.trade_plan is None


def test_score_candidate_uses_historical_prediction_estimate():
    estimate = PredictionEstimate(
        next_day_up_probability=0.61,
        three_day_up_probability=0.68,
        expected_return=2.35,
        sample_count=12,
        source="history",
    )

    candidate = score_candidate(make_quote(), AppSettings(), prediction_estimate=estimate)

    assert candidate.next_day_up_probability == 0.61
    assert candidate.three_day_up_probability == 0.68
    assert candidate.expected_return == 2.35
    assert "12个历史相似样本" in candidate.reason
