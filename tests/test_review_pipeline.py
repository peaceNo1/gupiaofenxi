from datetime import date

from gupiaofenxi.domain.models import (
    CandidateReview,
    ReviewPrice,
    ReviewState,
    ReviewStatus,
    TradePlan,
)


def test_review_models_hold_candidate_snapshot_and_price_history():
    review = CandidateReview(
        report_date=date(2026, 5, 20),
        symbol="000001",
        name="平安银行",
        start_price=10.0,
        score=76.5,
        label="强烈关注",
        next_day_up_probability=0.57,
        three_day_up_probability=0.62,
        expected_return=2.6,
        trade_plan=TradePlan(
            buy_low=9.7,
            buy_high=9.9,
            stop_loss=9.2,
            target_price=10.8,
            trigger="回踩低吸区间观察",
        ),
    )
    state = ReviewState(
        reviews=[review],
        prices=[
            ReviewPrice(
                trade_date=date(2026, 5, 21),
                symbol="000001",
                close=10.5,
                high=10.9,
                low=9.8,
            )
        ],
    )

    assert state.reviews[0].review_status == ReviewStatus.WAITING
    assert state.prices[0].symbol == "000001"
