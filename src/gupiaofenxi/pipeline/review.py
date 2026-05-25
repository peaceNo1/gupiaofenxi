from datetime import date

from gupiaofenxi.domain.models import (
    CandidateReview,
    DashboardReport,
    ReviewPrice,
    ReviewState,
    ReviewStatus,
    ReviewSummary,
    StockQuote,
)


def merge_review_snapshots(state: ReviewState, report: DashboardReport) -> ReviewState:
    reviews_by_key = {(item.report_date, item.symbol): item for item in state.reviews}

    for candidate in report.candidates:
        key = (report.report_date, candidate.symbol)
        existing = reviews_by_key.get(key)
        review = CandidateReview(
            report_date=report.report_date,
            symbol=candidate.symbol,
            name=candidate.name,
            start_price=candidate.current_price,
            score=candidate.score,
            label=str(candidate.label.value),
            next_day_up_probability=candidate.next_day_up_probability,
            three_day_up_probability=candidate.three_day_up_probability,
            expected_return=candidate.expected_return,
            trade_plan=candidate.trade_plan,
        )
        if existing:
            review = review.model_copy(
                update={
                    "next_day_return": existing.next_day_return,
                    "three_day_return": existing.three_day_return,
                    "five_day_return": existing.five_day_return,
                    "touched_buy_zone": existing.touched_buy_zone,
                    "touched_target": existing.touched_target,
                    "touched_stop_loss": existing.touched_stop_loss,
                    "review_status": existing.review_status,
                }
            )
        reviews_by_key[key] = review

    return ReviewState(
        reviews=sorted(reviews_by_key.values(), key=lambda item: (item.report_date, item.symbol)),
        prices=state.prices,
    )


def record_price_history(state: ReviewState, quotes: list[StockQuote]) -> ReviewState:
    prices_by_key = {(item.trade_date, item.symbol): item for item in state.prices}
    for quote in quotes:
        prices_by_key[(quote.trade_date, quote.symbol)] = ReviewPrice(
            trade_date=quote.trade_date,
            symbol=quote.symbol,
            close=quote.close,
            high=quote.high,
            low=quote.low,
        )
    return ReviewState(
        reviews=state.reviews,
        prices=sorted(prices_by_key.values(), key=lambda item: (item.trade_date, item.symbol)),
    )


def update_review_outcomes(state: ReviewState) -> ReviewState:
    prices_by_symbol: dict[str, list[ReviewPrice]] = {}
    for price in state.prices:
        prices_by_symbol.setdefault(price.symbol, []).append(price)
    for prices in prices_by_symbol.values():
        prices.sort(key=lambda item: item.trade_date)

    return ReviewState(
        reviews=[_update_review_outcome(review, prices_by_symbol.get(review.symbol, [])) for review in state.reviews],
        prices=state.prices,
    )


def build_review_summary(reviews: list[CandidateReview]) -> ReviewSummary:
    next_day_returns = [item.next_day_return for item in reviews if item.next_day_return is not None]
    three_day_returns = [item.three_day_return for item in reviews if item.three_day_return is not None]
    five_day_returns = [item.five_day_return for item in reviews if item.five_day_return is not None]
    return ReviewSummary(
        total_count=len(reviews),
        next_day_count=len(next_day_returns),
        next_day_up_rate=_up_rate(next_day_returns),
        three_day_count=len(three_day_returns),
        three_day_up_rate=_up_rate(three_day_returns),
        five_day_count=len(five_day_returns),
        five_day_up_rate=_up_rate(five_day_returns),
        target_touch_count=sum(1 for item in reviews if item.touched_target is True),
        stop_loss_touch_count=sum(1 for item in reviews if item.touched_stop_loss is True),
    )


def filter_reviews(
    reviews: list[CandidateReview],
    report_date: date | None = None,
    label: str = "",
    result: str = "all",
) -> list[CandidateReview]:
    filtered = reviews
    if report_date is not None:
        filtered = [item for item in filtered if item.report_date == report_date]
    if label:
        filtered = [item for item in filtered if item.label == label]

    if result == "up":
        filtered = [item for item in filtered if item.next_day_return is not None and item.next_day_return > 0]
    elif result == "down":
        filtered = [item for item in filtered if item.next_day_return is not None and item.next_day_return <= 0]
    elif result == "target":
        filtered = [item for item in filtered if item.touched_target is True]
    elif result == "stop":
        filtered = [item for item in filtered if item.touched_stop_loss is True]
    elif result == "waiting":
        filtered = [item for item in filtered if item.review_status == ReviewStatus.WAITING]

    return sorted(filtered, key=lambda item: (item.report_date, item.score), reverse=True)


def _update_review_outcome(review: CandidateReview, prices: list[ReviewPrice]) -> CandidateReview:
    future = [price for price in prices if price.trade_date > review.report_date]
    first_five = future[:5]
    invalid_start_price = review.start_price <= 0
    if not future:
        return review.model_copy(
            update={
                "next_day_return": None,
                "three_day_return": None,
                "five_day_return": None,
                "touched_buy_zone": None,
                "touched_target": None,
                "touched_stop_loss": None,
                "review_status": ReviewStatus.WAITING,
            }
        )

    return review.model_copy(
        update={
            "next_day_return": _return_pct(review.start_price, future, 1),
            "three_day_return": _return_pct(review.start_price, future, 3),
            "five_day_return": _return_pct(review.start_price, future, 5),
            "touched_buy_zone": _touched_buy_zone(first_five, review),
            "touched_target": _touched_target(first_five, review),
            "touched_stop_loss": _touched_stop_loss(first_five, review),
            "review_status": ReviewStatus.MISSING_DATA
            if invalid_start_price
            else ReviewStatus.COMPLETE
            if len(future) >= 5
            else ReviewStatus.PARTIAL,
        }
    )


def _return_pct(start_price: float, future: list[ReviewPrice], day: int) -> float | None:
    if start_price <= 0 or len(future) < day:
        return None
    close = future[day - 1].close
    return round((close - start_price) / start_price * 100, 2)


def _touched_buy_zone(prices: list[ReviewPrice], review: CandidateReview) -> bool | None:
    plan = review.trade_plan
    if not plan or not prices:
        return None
    return any(price.low <= plan.buy_high and price.high >= plan.buy_low for price in prices)


def _touched_target(prices: list[ReviewPrice], review: CandidateReview) -> bool | None:
    plan = review.trade_plan
    if not plan or not prices:
        return None
    return any(price.high >= plan.target_price for price in prices)


def _touched_stop_loss(prices: list[ReviewPrice], review: CandidateReview) -> bool | None:
    plan = review.trade_plan
    if not plan or not prices:
        return None
    return any(price.low <= plan.stop_loss for price in prices)


def _up_rate(returns: list[float]) -> float | None:
    if not returns:
        return None
    return round(sum(1 for value in returns if value > 0) / len(returns) * 100, 2)
