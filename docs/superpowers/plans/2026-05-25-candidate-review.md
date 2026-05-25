# Candidate Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local candidate review system that snapshots every candidate, stores daily quote history, computes next-day/3-day/5-day outcomes and trade-plan touches, and renders a homepage summary plus `/reviews` detail page.

**Architecture:** Add focused review domain models, a review calculation module, and JSON persistence methods. The web app updates reviews after every report generation by saving today's candidates and today's full quote snapshot, then recalculating old outcomes from local quote history.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, Jinja2, local JSON storage, pytest.

---

## File Structure

- Create `src/gupiaofenxi/pipeline/review.py`: pure review functions for snapshot creation, price history recording, outcome calculation, summaries, and filters.
- Modify `src/gupiaofenxi/domain/models.py`: add review models and status enum.
- Modify `src/gupiaofenxi/storage/json_store.py`: persist and load review state in `data/local/reviews.json`.
- Modify `src/gupiaofenxi/web/app.py`: update reviews during report generation and add `/reviews` route.
- Modify `src/gupiaofenxi/web/templates/dashboard.html`: render homepage review summary.
- Create `src/gupiaofenxi/web/templates/reviews.html`: render the detail review page.
- Add tests in `tests/test_review_pipeline.py`, `tests/test_json_store.py`, and `tests/test_web_app.py`.

---

### Task 1: Review Domain Models

**Files:**
- Modify: `src/gupiaofenxi/domain/models.py`
- Test: `tests/test_review_pipeline.py`

- [ ] **Step 1: Write failing model/construction test**

Create `tests/test_review_pipeline.py` with:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_review_pipeline.py::test_review_models_hold_candidate_snapshot_and_price_history -q`

Expected: FAIL with `ImportError` or `cannot import name 'CandidateReview'`.

- [ ] **Step 3: Add review models**

In `src/gupiaofenxi/domain/models.py`, after `AlertItem`, add:

```python
class ReviewStatus(str, Enum):
    WAITING = "等待数据"
    PARTIAL = "部分完成"
    COMPLETE = "已完成"
    MISSING_DATA = "缺少行情"


class ReviewPrice(BaseModel):
    trade_date: date
    symbol: str
    close: float
    high: float
    low: float


class CandidateReview(BaseModel):
    report_date: date
    symbol: str
    name: str
    start_price: float
    score: float
    label: str
    next_day_up_probability: float
    three_day_up_probability: float
    expected_return: float
    trade_plan: TradePlan | None = None
    next_day_return: float | None = None
    three_day_return: float | None = None
    five_day_return: float | None = None
    touched_buy_zone: bool | None = None
    touched_target: bool | None = None
    touched_stop_loss: bool | None = None
    review_status: ReviewStatus = ReviewStatus.WAITING


class ReviewSummary(BaseModel):
    total_count: int = 0
    next_day_count: int = 0
    next_day_up_rate: float | None = None
    three_day_count: int = 0
    three_day_up_rate: float | None = None
    five_day_count: int = 0
    five_day_up_rate: float | None = None
    target_touch_count: int = 0
    stop_loss_touch_count: int = 0


class ReviewState(BaseModel):
    reviews: list[CandidateReview] = []
    prices: list[ReviewPrice] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests\test_review_pipeline.py::test_review_models_hold_candidate_snapshot_and_price_history -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src\gupiaofenxi\domain\models.py tests\test_review_pipeline.py
git commit -m "feat: add candidate review models"
```

---

### Task 2: Review Calculation Pipeline

**Files:**
- Create: `src/gupiaofenxi/pipeline/review.py`
- Test: `tests/test_review_pipeline.py`

- [ ] **Step 1: Add failing tests for snapshots, price history, outcomes, and summary**

Append to `tests/test_review_pipeline.py`:

```python
from datetime import datetime

from gupiaofenxi.domain.models import CandidateLabel, CandidateScore, DashboardReport, DataStatusRecord, DataTaskStatus, StockQuote
from gupiaofenxi.pipeline.review import (
    build_review_summary,
    filter_reviews,
    merge_review_snapshots,
    record_price_history,
    update_review_outcomes,
)


def _candidate(symbol="000001", price=10.0):
    return CandidateScore(
        symbol=symbol,
        name="平安银行",
        current_price=price,
        daily_pct_change=1.2,
        score=76.5,
        next_day_up_probability=0.57,
        three_day_up_probability=0.62,
        expected_return=2.6,
        label=CandidateLabel.STRONG_WATCH,
        reason="test",
        strength_score=20,
        dip_position_score=20,
        sentiment_score=20,
        historical_similarity_score=16.5,
        trade_plan=TradePlan(
            buy_low=9.7,
            buy_high=9.9,
            stop_loss=9.2,
            target_price=10.8,
            trigger="回踩低吸区间观察",
        ),
    )


def _report(report_date, candidates):
    return DashboardReport(
        report_date=report_date,
        generated_at=datetime.combine(report_date, datetime.min.time()),
        market_temperature="偏强",
        strong_pool_count=len(candidates),
        high_score_count=len(candidates),
        risk_count=0,
        price_range=(3, 60),
        data_status=[
            DataStatusRecord(
                task_name="日线行情",
                source_name="test",
                status=DataTaskStatus.SUCCESS,
                started_at=datetime.combine(report_date, datetime.min.time()),
                ended_at=datetime.combine(report_date, datetime.min.time()),
                message="ok",
            )
        ],
        candidates=candidates,
    )


def test_review_pipeline_snapshots_candidates_idempotently():
    state = ReviewState()
    report = _report(date(2026, 5, 20), [_candidate()])

    state = merge_review_snapshots(state, report)
    state = merge_review_snapshots(state, report)

    assert len(state.reviews) == 1
    review = state.reviews[0]
    assert review.symbol == "000001"
    assert review.start_price == 10.0
    assert review.label == "强烈关注"


def test_review_pipeline_records_price_history_idempotently():
    state = ReviewState()
    quotes = [
        StockQuote(
            symbol="000001",
            name="平安银行",
            trade_date=date(2026, 5, 21),
            open=10,
            high=10.9,
            low=9.8,
            close=10.5,
            volume=1000,
            amount=100000000,
            pct_change=5,
        )
    ]

    state = record_price_history(state, quotes)
    state = record_price_history(state, quotes)

    assert len(state.prices) == 1
    assert state.prices[0].high == 10.9


def test_review_pipeline_calculates_returns_and_trade_plan_touches():
    state = merge_review_snapshots(ReviewState(), _report(date(2026, 5, 20), [_candidate()]))
    state = record_price_history(
        state,
        [
            StockQuote(symbol="000001", name="平安银行", trade_date=date(2026, 5, 21), open=10, high=10.9, low=9.8, close=10.5, volume=1, amount=1, pct_change=5),
            StockQuote(symbol="000001", name="平安银行", trade_date=date(2026, 5, 23), open=10, high=11.0, low=9.6, close=10.8, volume=1, amount=1, pct_change=3),
            StockQuote(symbol="000001", name="平安银行", trade_date=date(2026, 5, 25), open=10, high=11.2, low=9.1, close=9.5, volume=1, amount=1, pct_change=-12),
        ],
    )

    state = update_review_outcomes(state)
    review = state.reviews[0]

    assert review.next_day_return == 5.0
    assert review.three_day_return == 8.0
    assert review.five_day_return == -5.0
    assert review.touched_buy_zone is True
    assert review.touched_target is True
    assert review.touched_stop_loss is True
    assert review.review_status.value == "已完成"


def test_review_summary_excludes_waiting_denominators_and_filters():
    completed = CandidateReview(
        report_date=date(2026, 5, 20),
        symbol="000001",
        name="平安银行",
        start_price=10,
        score=76,
        label="强烈关注",
        next_day_up_probability=0.57,
        three_day_up_probability=0.62,
        expected_return=2.6,
        next_day_return=5,
        three_day_return=-1,
        five_day_return=2,
        touched_target=True,
        touched_stop_loss=False,
        review_status=ReviewStatus.COMPLETE,
    )
    waiting = completed.model_copy(update={"symbol": "000002", "next_day_return": None, "review_status": ReviewStatus.WAITING})
    state = ReviewState(reviews=[completed, waiting])

    summary = build_review_summary(state.reviews)
    filtered = filter_reviews(state.reviews, result="target")

    assert summary.total_count == 2
    assert summary.next_day_count == 1
    assert summary.next_day_up_rate == 100.0
    assert summary.three_day_up_rate == 0.0
    assert summary.target_touch_count == 1
    assert [item.symbol for item in filtered] == ["000001"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_review_pipeline.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'gupiaofenxi.pipeline.review'`.

- [ ] **Step 3: Implement review pipeline**

Create `src/gupiaofenxi/pipeline/review.py`:

```python
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
    reviews = {(item.report_date, item.symbol): item for item in state.reviews}
    for candidate in report.candidates:
        key = (report.report_date, candidate.symbol)
        reviews[key] = CandidateReview(
            report_date=report.report_date,
            symbol=candidate.symbol,
            name=candidate.name,
            start_price=candidate.current_price,
            score=candidate.score,
            label=candidate.label.value,
            next_day_up_probability=candidate.next_day_up_probability,
            three_day_up_probability=candidate.three_day_up_probability,
            expected_return=candidate.expected_return,
            trade_plan=candidate.trade_plan,
            next_day_return=reviews.get(key).next_day_return if key in reviews else None,
            three_day_return=reviews.get(key).three_day_return if key in reviews else None,
            five_day_return=reviews.get(key).five_day_return if key in reviews else None,
            touched_buy_zone=reviews.get(key).touched_buy_zone if key in reviews else None,
            touched_target=reviews.get(key).touched_target if key in reviews else None,
            touched_stop_loss=reviews.get(key).touched_stop_loss if key in reviews else None,
            review_status=reviews.get(key).review_status if key in reviews else ReviewStatus.WAITING,
        )
    return ReviewState(reviews=sorted(reviews.values(), key=lambda item: (item.report_date, item.symbol)), prices=state.prices)


def record_price_history(state: ReviewState, quotes: list[StockQuote]) -> ReviewState:
    prices = {(item.trade_date, item.symbol): item for item in state.prices}
    for quote in quotes:
        prices[(quote.trade_date, quote.symbol)] = ReviewPrice(
            trade_date=quote.trade_date,
            symbol=quote.symbol,
            close=quote.close,
            high=quote.high,
            low=quote.low,
        )
    return ReviewState(reviews=state.reviews, prices=sorted(prices.values(), key=lambda item: (item.trade_date, item.symbol)))


def update_review_outcomes(state: ReviewState) -> ReviewState:
    prices_by_symbol: dict[str, list[ReviewPrice]] = {}
    for price in state.prices:
        prices_by_symbol.setdefault(price.symbol, []).append(price)
    for rows in prices_by_symbol.values():
        rows.sort(key=lambda item: item.trade_date)

    updated: list[CandidateReview] = []
    for review in state.reviews:
        future = [
            price
            for price in prices_by_symbol.get(review.symbol, [])
            if price.trade_date > review.report_date
        ]
        next_day = _nth_future(future, 1)
        three_day = _nth_future(future, 3)
        five_day = _nth_future(future, 5)
        touched_buy_zone, touched_target, touched_stop_loss = _trade_plan_touches(review, future[:5])
        status = _review_status(future)
        updated.append(
            review.model_copy(
                update={
                    "next_day_return": _return_pct(review.start_price, next_day),
                    "three_day_return": _return_pct(review.start_price, three_day),
                    "five_day_return": _return_pct(review.start_price, five_day),
                    "touched_buy_zone": touched_buy_zone,
                    "touched_target": touched_target,
                    "touched_stop_loss": touched_stop_loss,
                    "review_status": status,
                }
            )
        )
    return ReviewState(reviews=updated, prices=state.prices)


def build_review_summary(reviews: list[CandidateReview]) -> ReviewSummary:
    next_day = [item for item in reviews if item.next_day_return is not None]
    three_day = [item for item in reviews if item.three_day_return is not None]
    five_day = [item for item in reviews if item.five_day_return is not None]
    return ReviewSummary(
        total_count=len(reviews),
        next_day_count=len(next_day),
        next_day_up_rate=_up_rate(next_day, "next_day_return"),
        three_day_count=len(three_day),
        three_day_up_rate=_up_rate(three_day, "three_day_return"),
        five_day_count=len(five_day),
        five_day_up_rate=_up_rate(five_day, "five_day_return"),
        target_touch_count=sum(item.touched_target is True for item in reviews),
        stop_loss_touch_count=sum(item.touched_stop_loss is True for item in reviews),
    )


def filter_reviews(
    reviews: list[CandidateReview],
    report_date: date | None = None,
    label: str = "",
    result: str = "all",
) -> list[CandidateReview]:
    rows = list(reviews)
    if report_date:
        rows = [item for item in rows if item.report_date == report_date]
    if label:
        rows = [item for item in rows if item.label == label]
    if result == "up":
        rows = [item for item in rows if (item.next_day_return or 0) > 0]
    elif result == "down":
        rows = [item for item in rows if item.next_day_return is not None and item.next_day_return <= 0]
    elif result == "target":
        rows = [item for item in rows if item.touched_target is True]
    elif result == "stop":
        rows = [item for item in rows if item.touched_stop_loss is True]
    elif result == "waiting":
        rows = [item for item in rows if item.review_status == ReviewStatus.WAITING]
    return sorted(rows, key=lambda item: (item.report_date, item.score), reverse=True)


def _nth_future(future: list[ReviewPrice], day_number: int) -> ReviewPrice | None:
    index = day_number - 1
    return future[index] if len(future) > index else None


def _return_pct(start_price: float, price: ReviewPrice | None) -> float | None:
    if not price or start_price <= 0:
        return None
    return round((price.close - start_price) / start_price * 100, 2)


def _trade_plan_touches(review: CandidateReview, future: list[ReviewPrice]) -> tuple[bool | None, bool | None, bool | None]:
    if not review.trade_plan or not future:
        return None, None, None
    plan = review.trade_plan
    touched_buy = any(price.low <= plan.buy_high and price.high >= plan.buy_low for price in future)
    touched_target = any(price.high >= plan.target_price for price in future)
    touched_stop = any(price.low <= plan.stop_loss for price in future)
    return touched_buy, touched_target, touched_stop


def _review_status(future: list[ReviewPrice]) -> ReviewStatus:
    if not future:
        return ReviewStatus.WAITING
    if len(future) >= 5:
        return ReviewStatus.COMPLETE
    return ReviewStatus.PARTIAL


def _up_rate(reviews: list[CandidateReview], field: str) -> float | None:
    if not reviews:
        return None
    up_count = sum((getattr(item, field) or 0) > 0 for item in reviews)
    return round(up_count / len(reviews) * 100, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests\test_review_pipeline.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src\gupiaofenxi\pipeline\review.py tests\test_review_pipeline.py
git commit -m "feat: calculate candidate review outcomes"
```

---

### Task 3: JSON Persistence For Reviews

**Files:**
- Modify: `src/gupiaofenxi/storage/json_store.py`
- Test: `tests/test_json_store.py`

- [ ] **Step 1: Add failing persistence test**

Append to `tests/test_json_store.py`:

```python
from datetime import date

from gupiaofenxi.domain.models import CandidateReview, ReviewPrice, ReviewState


def test_json_store_persists_review_state(tmp_path: Path):
    store = JsonStore(tmp_path)
    state = ReviewState(
        reviews=[
            CandidateReview(
                report_date=date(2026, 5, 20),
                symbol="000001",
                name="平安银行",
                start_price=10.0,
                score=76,
                label="强烈关注",
                next_day_up_probability=0.57,
                three_day_up_probability=0.62,
                expected_return=2.6,
            )
        ],
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

    store.save_review_state(state)
    loaded = store.load_review_state()

    assert loaded.reviews[0].symbol == "000001"
    assert loaded.prices[0].close == 10.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_json_store.py::test_json_store_persists_review_state -q`

Expected: FAIL with `AttributeError: 'JsonStore' object has no attribute 'save_review_state'`.

- [ ] **Step 3: Implement store methods**

In `src/gupiaofenxi/storage/json_store.py`, update import:

```python
from gupiaofenxi.domain.models import DashboardReport, ManualOverride, Position, ReviewState
```

Add after `positions_path`:

```python
    @property
    def reviews_path(self) -> Path:
        return self.root / "reviews.json"
```

Add before `save_report`:

```python
    def load_review_state(self) -> ReviewState:
        if not self.reviews_path.exists():
            return ReviewState()
        payload = json.loads(self.reviews_path.read_text(encoding="utf-8"))
        return ReviewState(**payload)

    def save_review_state(self, state: ReviewState) -> None:
        self.reviews_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests\test_json_store.py::test_json_store_persists_review_state -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src\gupiaofenxi\storage\json_store.py tests\test_json_store.py
git commit -m "feat: persist candidate review state"
```

---

### Task 4: Integrate Reviews Into Report Generation

**Files:**
- Modify: `src/gupiaofenxi/web/app.py`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Add failing integration test**

Append to `tests/test_web_app.py`:

```python
def test_dashboard_generation_updates_candidate_reviews(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/")

    assert response.status_code == 200
    review_path = tmp_path / "reviews.json"
    assert review_path.exists()
    payload = review_path.read_text(encoding="utf-8")
    assert "reviews" in payload
    assert "prices" in payload
    assert "000001" in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_web_app.py::test_dashboard_generation_updates_candidate_reviews -q`

Expected: FAIL because `reviews.json` does not exist.

- [ ] **Step 3: Update app report generation**

In `src/gupiaofenxi/web/app.py`, add import:

```python
from gupiaofenxi.pipeline.review import (
    build_review_summary,
    filter_reviews,
    merge_review_snapshots,
    record_price_history,
    update_review_outcomes,
)
```

Inside `create_app`, add helper after `report_payload`:

```python
    def refresh_review_state(report: DashboardReport) -> None:
        state = store.load_review_state()
        quotes, _ = provider_factory().load_daily_quotes()
        state = merge_review_snapshots(state, report)
        state = record_price_history(state, quotes)
        state = update_review_outcomes(state)
        store.save_review_state(state)
```

Inside `generate_report_with_filters`, after `store.save_report(report)`, add:

```python
        refresh_review_state(report)
```

Do not call `refresh_review_state` before `save_report`; the report must exist even if review updating fails later.

- [ ] **Step 4: Run integration test**

Run: `python -m pytest tests\test_web_app.py::test_dashboard_generation_updates_candidate_reviews -q`

Expected: PASS.

- [ ] **Step 5: Run related tests**

Run: `python -m pytest tests\test_web_app.py tests\test_json_store.py tests\test_review_pipeline.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\gupiaofenxi\web\app.py tests\test_web_app.py
git commit -m "feat: update reviews during report generation"
```

---

### Task 5: Homepage Review Summary

**Files:**
- Modify: `src/gupiaofenxi/web/app.py`
- Modify: `src/gupiaofenxi/web/templates/dashboard.html`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Add failing homepage summary test**

Append to `tests/test_web_app.py`:

```python
def test_dashboard_renders_review_summary(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))

    response = client.get("/")

    assert response.status_code == 200
    assert "复盘统计" in response.text
    assert "次日上涨率" in response.text
    assert "/reviews" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_web_app.py::test_dashboard_renders_review_summary -q`

Expected: FAIL because the dashboard does not contain `复盘统计`.

- [ ] **Step 3: Pass summary to template**

In `dashboard()` route in `src/gupiaofenxi/web/app.py`, before `TemplateResponse`, add:

```python
        review_state = store.load_review_state()
        review_summary = build_review_summary(review_state.reviews)
```

Add to template context:

```python
                "review_summary": review_summary,
```

- [ ] **Step 4: Render summary in dashboard template**

In `src/gupiaofenxi/web/templates/dashboard.html`, after the main metrics `<section class="metrics">...</section>`, add:

```html
      <section class="metrics">
        <div><strong>{{ review_summary.total_count }}</strong><span>复盘样本</span></div>
        <div><strong>{{ "%.1f"|format(review_summary.next_day_up_rate or 0) }}%</strong><span>次日上涨率</span></div>
        <div><strong>{{ "%.1f"|format(review_summary.three_day_up_rate or 0) }}%</strong><span>3日上涨率</span></div>
        <div><strong>{{ "%.1f"|format(review_summary.five_day_up_rate or 0) }}%</strong><span>5日上涨率</span></div>
        <div><strong>{{ review_summary.target_touch_count }}/{{ review_summary.stop_loss_touch_count }}</strong><span>目标/止损</span></div>
      </section>
      <section class="table-wrap">
        <h2>复盘统计</h2>
        <p>已记录 {{ review_summary.total_count }} 条候选股复盘样本，<a href="/reviews">查看复盘明细</a></p>
      </section>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests\test_web_app.py::test_dashboard_renders_review_summary -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\gupiaofenxi\web\app.py src\gupiaofenxi\web\templates\dashboard.html tests\test_web_app.py
git commit -m "feat: show candidate review summary"
```

---

### Task 6: Review Detail Page

**Files:**
- Modify: `src/gupiaofenxi/web/app.py`
- Create: `src/gupiaofenxi/web/templates/reviews.html`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Add failing detail page test**

Append to `tests/test_web_app.py`:

```python
def test_reviews_page_renders_detail_table_and_filters(tmp_path):
    client = TestClient(create_app(store_root=tmp_path, provider_factory=sample_provider_factory))
    client.get("/")

    response = client.get("/reviews?result=waiting")

    assert response.status_code == 200
    assert "复盘明细" in response.text
    assert 'name="result"' in response.text
    assert "000001" in response.text
    assert "次日涨跌" in response.text
    assert "等待数据" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_web_app.py::test_reviews_page_renders_detail_table_and_filters -q`

Expected: FAIL with 404 or missing text.

- [ ] **Step 3: Add route**

In `src/gupiaofenxi/web/app.py`, add `from datetime import date` near imports.

Add route before `/api/report`:

```python
    @app.get("/reviews", response_class=HTMLResponse)
    def reviews_page(
        request: Request,
        report_date: str = "",
        label: str = "",
        result: str = "all",
    ):
        state = store.load_review_state()
        parsed_date = date.fromisoformat(report_date) if report_date else None
        rows = filter_reviews(state.reviews, report_date=parsed_date, label=label, result=result)
        summary = build_review_summary(state.reviews)
        labels = sorted({item.label for item in state.reviews})
        dates = sorted({item.report_date.isoformat() for item in state.reviews}, reverse=True)
        return templates.TemplateResponse(
            request,
            "reviews.html",
            {
                "reviews": rows,
                "summary": summary,
                "labels": labels,
                "dates": dates,
                "selected_date": report_date,
                "selected_label": label,
                "selected_result": result,
            },
        )
```

- [ ] **Step 4: Create template**

Create `src/gupiaofenxi/web/templates/reviews.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>复盘明细</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body>
    <main class="page">
      <header class="topbar">
        <div>
          <h1>复盘明细</h1>
          <p>验证候选股次日、3日、5日表现和交易计划触达情况</p>
        </div>
        <a href="/">返回仪表盘</a>
      </header>

      <section class="metrics">
        <div><strong>{{ summary.total_count }}</strong><span>复盘样本</span></div>
        <div><strong>{{ "%.1f"|format(summary.next_day_up_rate or 0) }}%</strong><span>次日上涨率</span></div>
        <div><strong>{{ "%.1f"|format(summary.three_day_up_rate or 0) }}%</strong><span>3日上涨率</span></div>
        <div><strong>{{ "%.1f"|format(summary.five_day_up_rate or 0) }}%</strong><span>5日上涨率</span></div>
        <div><strong>{{ summary.target_touch_count }}/{{ summary.stop_loss_touch_count }}</strong><span>目标/止损</span></div>
      </section>

      <form class="filters" method="get" action="/reviews">
        <label>日期
          <select name="report_date">
            <option value="">全部</option>
            {% for item in dates %}
              <option value="{{ item }}" {% if item == selected_date %}selected{% endif %}>{{ item }}</option>
            {% endfor %}
          </select>
        </label>
        <label>标签
          <select name="label">
            <option value="">全部</option>
            {% for item in labels %}
              <option value="{{ item }}" {% if item == selected_label %}selected{% endif %}>{{ item }}</option>
            {% endfor %}
          </select>
        </label>
        <label>结果
          <select name="result">
            {% for value, text in [("all", "全部"), ("up", "次日上涨"), ("down", "次日下跌"), ("target", "触达目标"), ("stop", "触发止损"), ("waiting", "等待数据")] %}
              <option value="{{ value }}" {% if value == selected_result %}selected{% endif %}>{{ text }}</option>
            {% endfor %}
          </select>
        </label>
        <button type="submit">应用</button>
      </form>

      <section class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>代码</th>
              <th>名称</th>
              <th>起始价</th>
              <th>综合分</th>
              <th>标签</th>
              <th>次日涨跌</th>
              <th>3日涨跌</th>
              <th>5日涨跌</th>
              <th>低吸区间</th>
              <th>目标</th>
              <th>止损</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {% for item in reviews %}
              <tr>
                <td>{{ item.report_date }}</td>
                <td>{{ item.symbol }}</td>
                <td>{{ item.name }}</td>
                <td>{{ "%.2f"|format(item.start_price) }}</td>
                <td>{{ "%.2f"|format(item.score) }}</td>
                <td>{{ item.label }}</td>
                <td>{{ "%.2f"|format(item.next_day_return) ~ "%" if item.next_day_return is not none else "等待数据" }}</td>
                <td>{{ "%.2f"|format(item.three_day_return) ~ "%" if item.three_day_return is not none else "等待数据" }}</td>
                <td>{{ "%.2f"|format(item.five_day_return) ~ "%" if item.five_day_return is not none else "等待数据" }}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.buy_low }}-{{ item.trade_plan.buy_high }}{% else %}-{% endif %}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.target_price }}{% else %}-{% endif %}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.stop_loss }}{% else %}-{% endif %}</td>
                <td>{{ item.review_status.value }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests\test_web_app.py::test_reviews_page_renders_detail_table_and_filters -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\gupiaofenxi\web\app.py src\gupiaofenxi\web\templates\reviews.html tests\test_web_app.py
git commit -m "feat: add candidate review detail page"
```

---

### Task 7: Final Verification

**Files:**
- No new source files unless verification finds a defect.

- [ ] **Step 1: Run full tests**

Run: `python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 2: Restart local server**

Run:

```powershell
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) { $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
Start-Process -FilePath python -ArgumentList @('-m','uvicorn','gupiaofenxi.web.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory 'D:\codex\股票量化分析' -WindowStyle Hidden
Start-Sleep -Seconds 3
```

- [ ] **Step 3: Verify endpoints**

Run:

```powershell
(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/').StatusCode
(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/reviews').StatusCode
```

Expected: both return `200`.

- [ ] **Step 4: Commit any verification fixes**

If any defect was fixed during verification:

```powershell
git add src\gupiaofenxi tests
git commit -m "fix: stabilize candidate review feature"
```

- [ ] **Step 5: Push**

Run:

```powershell
git push origin main
```

Expected: push succeeds.

---

## Self-Review

- Spec coverage: The plan covers all-candidate snapshots, local `reviews.json`, next/3/5-day returns, buy-zone/target/stop touches, homepage summary, `/reviews` detail filters, waiting data handling, duplicate prevention, and tests.
- Scope check: This is one coherent subsystem. It does not include brokerage integration, trade execution, portfolio advice, or cloud storage.
- Type consistency: `CandidateReview`, `ReviewPrice`, `ReviewState`, `ReviewSummary`, and `ReviewStatus` are introduced before use. Pipeline functions use those names consistently.
- Important implementation note: the plan stores daily full quote history in the review state so that all candidates can be reviewed even if they do not appear in later candidate lists.
