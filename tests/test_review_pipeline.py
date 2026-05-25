from datetime import date, datetime

from gupiaofenxi.domain.models import (
    CandidateLabel,
    CandidateReview,
    CandidateScore,
    DashboardReport,
    ReviewPrice,
    ReviewState,
    ReviewStatus,
    StockQuote,
    TradePlan,
)
from gupiaofenxi.pipeline.review import (
    build_review_summary,
    filter_reviews,
    merge_review_snapshots,
    record_price_history,
    update_review_outcomes,
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


def _candidate(
    symbol: str = "000001",
    current_price: float = 10.0,
    score: float = 88.0,
) -> CandidateScore:
    return CandidateScore(
        symbol=symbol,
        name="平安银行",
        current_price=current_price,
        daily_pct_change=2.1,
        score=score,
        next_day_up_probability=0.61,
        three_day_up_probability=0.66,
        expected_return=4.2,
        label=CandidateLabel.STRONG_WATCH,
        reason="日线行情偏强",
        strength_score=86.0,
        dip_position_score=82.0,
        sentiment_score=79.0,
        historical_similarity_score=81.0,
        trade_plan=TradePlan(
            buy_low=9.8,
            buy_high=10.0,
            stop_loss=9.4,
            target_price=10.8,
            trigger="回踩低吸区间观察",
        ),
    )


def _report(
    report_date: date = date(2026, 5, 20),
    candidates: list[CandidateScore] | None = None,
) -> DashboardReport:
    return DashboardReport(
        report_date=report_date,
        generated_at=datetime(2026, 5, 20, 15, 30),
        market_temperature="偏强",
        strong_pool_count=1,
        high_score_count=1,
        risk_count=0,
        price_range=(5.0, 30.0),
        data_status=[],
        candidates=candidates or [_candidate()],
    )


def _quote(symbol: str, trade_date: date, close: float, high: float, low: float) -> StockQuote:
    return StockQuote(
        symbol=symbol,
        name="平安银行",
        trade_date=trade_date,
        open=10.0,
        high=high,
        low=low,
        close=close,
        volume=1000000,
        amount=10000000,
        pct_change=1.2,
        industry="银行",
        concept="日线行情",
    )


def _review(
    symbol: str,
    report_date: date = date(2026, 5, 20),
    start_price: float = 10.0,
    score: float = 80.0,
    label: str = "alpha",
    next_day_return: float | None = None,
    touched_target: bool | None = None,
    touched_stop_loss: bool | None = None,
    review_status: ReviewStatus = ReviewStatus.WAITING,
    trade_plan: TradePlan | None = None,
) -> CandidateReview:
    return CandidateReview(
        report_date=report_date,
        symbol=symbol,
        name="review candidate",
        start_price=start_price,
        score=score,
        label=label,
        next_day_up_probability=0.61,
        three_day_up_probability=0.66,
        expected_return=4.2,
        trade_plan=trade_plan,
        next_day_return=next_day_return,
        touched_target=touched_target,
        touched_stop_loss=touched_stop_loss,
        review_status=review_status,
    )


def test_merge_review_snapshots_records_report_candidates_idempotently():
    previous = CandidateReview(
        report_date=date(2026, 5, 20),
        symbol="000001",
        name="平安银行",
        start_price=10.0,
        score=70.0,
        label=str(CandidateLabel.STRONG_WATCH.value),
        next_day_up_probability=0.51,
        three_day_up_probability=0.55,
        expected_return=2.0,
        touched_target=True,
        review_status=ReviewStatus.COMPLETE,
    )
    state = ReviewState(reviews=[previous])

    merged_once = merge_review_snapshots(
        state,
        _report(candidates=[_candidate(score=88.0), _candidate(symbol="000002", score=81.0)]),
    )
    merged_twice = merge_review_snapshots(
        merged_once,
        _report(candidates=[_candidate(score=88.0), _candidate(symbol="000002", score=81.0)]),
    )

    assert [(item.report_date, item.symbol) for item in merged_twice.reviews] == [
        (date(2026, 5, 20), "000001"),
        (date(2026, 5, 20), "000002"),
    ]
    assert len(merged_twice.reviews) == 2
    assert merged_twice.reviews[0].name == "平安银行"
    assert merged_twice.reviews[0].score == 88.0
    assert merged_twice.reviews[0].touched_target is True
    assert merged_twice.reviews[0].review_status == ReviewStatus.COMPLETE
    assert merged_twice.prices == []


def test_record_price_history_stores_quote_prices_idempotently():
    state = ReviewState()
    quotes = [
        _quote("000001", date(2026, 5, 22), close=10.7, high=10.9, low=10.2),
        _quote("000001", date(2026, 5, 21), close=10.5, high=10.6, low=9.9),
    ]

    recorded_once = record_price_history(state, quotes)
    recorded_twice = record_price_history(recorded_once, quotes)

    assert recorded_twice.prices == [
        ReviewPrice(
            trade_date=date(2026, 5, 21),
            symbol="000001",
            close=10.5,
            high=10.6,
            low=9.9,
        ),
        ReviewPrice(
            trade_date=date(2026, 5, 22),
            symbol="000001",
            close=10.7,
            high=10.9,
            low=10.2,
        ),
    ]


def test_update_review_outcomes_calculates_returns_and_trade_plan_touches():
    state = merge_review_snapshots(ReviewState(), _report())
    state = record_price_history(
        state,
        [
            _quote("000001", date(2026, 5, 21), close=10.5, high=10.6, low=9.9),
            _quote("000001", date(2026, 5, 22), close=10.6, high=10.9, low=10.1),
            _quote("000001", date(2026, 5, 23), close=10.3, high=10.4, low=10.0),
            _quote("000001", date(2026, 5, 24), close=9.8, high=10.0, low=9.3),
            _quote("000001", date(2026, 5, 25), close=9.5, high=9.9, low=9.4),
        ],
    )

    updated = update_review_outcomes(state)

    review = updated.reviews[0]
    assert review.next_day_return == 5.0
    assert review.three_day_return == 3.0
    assert review.five_day_return == -5.0
    assert review.touched_buy_zone is True
    assert review.touched_target is True
    assert review.touched_stop_loss is True
    assert review.review_status == ReviewStatus.COMPLETE


def test_update_review_outcomes_handles_waiting_partial_invalid_start_and_ignores_irrelevant_prices():
    plan = TradePlan(
        buy_low=9.8,
        buy_high=10.0,
        stop_loss=9.4,
        target_price=11.0,
        trigger="watch pullback",
    )
    state = ReviewState(
        reviews=[
            _review(
                "000001",
                next_day_return=99.0,
                touched_target=True,
                touched_stop_loss=True,
                review_status=ReviewStatus.COMPLETE,
                trade_plan=plan,
            ),
            _review("000002", trade_plan=plan),
            _review("000003", start_price=0.0, trade_plan=plan),
        ],
        prices=[
            ReviewPrice(trade_date=date(2026, 5, 19), symbol="000001", close=20.0, high=20.0, low=1.0),
            ReviewPrice(trade_date=date(2026, 5, 20), symbol="000001", close=21.0, high=21.0, low=1.0),
            ReviewPrice(trade_date=date(2026, 5, 21), symbol="999999", close=22.0, high=22.0, low=1.0),
            ReviewPrice(trade_date=date(2026, 5, 19), symbol="000002", close=30.0, high=30.0, low=1.0),
            ReviewPrice(trade_date=date(2026, 5, 20), symbol="000002", close=31.0, high=31.0, low=1.0),
            ReviewPrice(trade_date=date(2026, 5, 21), symbol="000002", close=10.4, high=10.5, low=9.9),
            ReviewPrice(trade_date=date(2026, 5, 22), symbol="000002", close=10.6, high=10.7, low=10.1),
            ReviewPrice(trade_date=date(2026, 5, 21), symbol="000003", close=1.0, high=11.1, low=9.9),
            ReviewPrice(trade_date=date(2026, 5, 22), symbol="000003", close=2.0, high=10.8, low=9.8),
            ReviewPrice(trade_date=date(2026, 5, 23), symbol="000003", close=3.0, high=10.7, low=9.7),
            ReviewPrice(trade_date=date(2026, 5, 24), symbol="000003", close=4.0, high=10.6, low=9.6),
            ReviewPrice(trade_date=date(2026, 5, 25), symbol="000003", close=5.0, high=10.5, low=9.5),
        ],
    )

    updated = update_review_outcomes(state)
    reviews = {item.symbol: item for item in updated.reviews}

    waiting = reviews["000001"]
    assert waiting.review_status == ReviewStatus.WAITING
    assert waiting.next_day_return is None
    assert waiting.three_day_return is None
    assert waiting.five_day_return is None
    assert waiting.touched_buy_zone is None
    assert waiting.touched_target is None
    assert waiting.touched_stop_loss is None

    partial = reviews["000002"]
    assert partial.review_status == ReviewStatus.PARTIAL
    assert partial.next_day_return == 4.0
    assert partial.three_day_return is None
    assert partial.five_day_return is None
    assert partial.touched_buy_zone is True
    assert partial.touched_target is False
    assert partial.touched_stop_loss is False

    invalid_start = reviews["000003"]
    assert invalid_start.review_status == ReviewStatus.COMPLETE
    assert invalid_start.next_day_return is None
    assert invalid_start.three_day_return is None
    assert invalid_start.five_day_return is None


def test_build_review_summary_excludes_waiting_denominators_and_filter_reviews_target_hits():
    reviews = [
        CandidateReview(
            report_date=date(2026, 5, 20),
            symbol="000001",
            name="平安银行",
            start_price=10.0,
            score=88.0,
            label=str(CandidateLabel.STRONG_WATCH.value),
            next_day_up_probability=0.61,
            three_day_up_probability=0.66,
            expected_return=4.2,
            next_day_return=5.0,
            three_day_return=3.0,
            five_day_return=None,
            touched_target=True,
            review_status=ReviewStatus.PARTIAL,
        ),
        CandidateReview(
            report_date=date(2026, 5, 21),
            symbol="000002",
            name="平安银行",
            start_price=10.0,
            score=82.0,
            label=str(CandidateLabel.STRONG_WATCH.value),
            next_day_up_probability=0.59,
            three_day_up_probability=0.62,
            expected_return=3.8,
            next_day_return=-1.0,
            three_day_return=None,
            five_day_return=None,
            touched_stop_loss=True,
            review_status=ReviewStatus.PARTIAL,
        ),
        CandidateReview(
            report_date=date(2026, 5, 22),
            symbol="000003",
            name="平安银行",
            start_price=10.0,
            score=91.0,
            label=str(CandidateLabel.STRONG_WATCH.value),
            next_day_up_probability=0.65,
            three_day_up_probability=0.69,
            expected_return=5.1,
            review_status=ReviewStatus.WAITING,
        ),
    ]

    summary = build_review_summary(reviews)
    target_hits = filter_reviews(reviews, result="target")

    assert summary.total_count == 3
    assert summary.next_day_count == 2
    assert summary.next_day_up_rate == 50.0
    assert summary.three_day_count == 1
    assert summary.three_day_up_rate == 100.0
    assert summary.five_day_count == 0
    assert summary.five_day_up_rate is None
    assert summary.target_touch_count == 1
    assert summary.stop_loss_touch_count == 1
    assert [item.symbol for item in target_hits] == ["000001"]


def test_filter_reviews_supports_results_labels_report_dates_and_descending_sort():
    reviews = [
        _review(
            "000001",
            report_date=date(2026, 5, 20),
            score=90.0,
            label="alpha",
            next_day_return=1.5,
            touched_target=True,
            review_status=ReviewStatus.PARTIAL,
        ),
        _review(
            "000002",
            report_date=date(2026, 5, 21),
            score=70.0,
            label="beta",
            next_day_return=-0.5,
            touched_stop_loss=True,
            review_status=ReviewStatus.PARTIAL,
        ),
        _review(
            "000003",
            report_date=date(2026, 5, 21),
            score=95.0,
            label="alpha",
            review_status=ReviewStatus.WAITING,
        ),
        _review(
            "000004",
            report_date=date(2026, 5, 22),
            score=60.0,
            label="alpha",
            next_day_return=0.0,
            review_status=ReviewStatus.COMPLETE,
        ),
    ]

    assert [item.symbol for item in filter_reviews(reviews, result="all")] == [
        "000004",
        "000003",
        "000002",
        "000001",
    ]
    assert [item.symbol for item in filter_reviews(reviews, result="up")] == ["000001"]
    assert [item.symbol for item in filter_reviews(reviews, result="down")] == ["000004", "000002"]
    assert [item.symbol for item in filter_reviews(reviews, result="target")] == ["000001"]
    assert [item.symbol for item in filter_reviews(reviews, result="stop")] == ["000002"]
    assert [item.symbol for item in filter_reviews(reviews, result="waiting")] == ["000003"]
    assert [item.symbol for item in filter_reviews(reviews, label="alpha")] == [
        "000004",
        "000003",
        "000001",
    ]
    assert [item.symbol for item in filter_reviews(reviews, report_date=date(2026, 5, 21))] == [
        "000003",
        "000002",
    ]
