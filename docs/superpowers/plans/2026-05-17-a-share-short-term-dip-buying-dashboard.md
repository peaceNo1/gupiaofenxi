# A Share Short-Term Dip Buying Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web dashboard that ranks A-share short-term dip-buying candidates from a recent-strong-stock pool, with price filtering, data status visibility, scores, probabilities, labels, and trade plans.

**Architecture:** Implement a Python backend with focused domain modules, deterministic test fixtures, and a small local web UI served by FastAPI. Keep data acquisition, data status logging, pool generation, scoring, trade planning, storage, and web presentation separate so each part can be tested independently.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, pandas, pydantic, pytest, JSON file storage, static HTML/CSS served locally.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, pytest config.
- `README.md`: local setup, run commands, and feature summary.
- `src/gupiaofenxi/__init__.py`: package marker.
- `src/gupiaofenxi/domain/models.py`: pydantic models and enums used across the app.
- `src/gupiaofenxi/config.py`: default user settings, including price range.
- `src/gupiaofenxi/data/status.py`: data status logger and current status summary.
- `src/gupiaofenxi/data/sample_provider.py`: deterministic local fixture provider for tests and first UI.
- `src/gupiaofenxi/pipeline/strong_pool.py`: recent-strong-stock pool generation and hard filters.
- `src/gupiaofenxi/pipeline/scoring.py`: score, probability, expected return, and label logic.
- `src/gupiaofenxi/pipeline/trade_plan.py`: low-buy range, stop loss, target, and trigger generation.
- `src/gupiaofenxi/pipeline/report.py`: orchestration that produces one dashboard report.
- `src/gupiaofenxi/storage/json_store.py`: JSON persistence for settings, manual overrides, status logs, and reports.
- `src/gupiaofenxi/web/app.py`: FastAPI app and API routes.
- `src/gupiaofenxi/web/templates/dashboard.html`: ranking-first dashboard page.
- `src/gupiaofenxi/web/static/styles.css`: local dashboard styling.
- `data/sample/daily_quotes.csv`: small deterministic A-share quote fixture.
- `data/sample/index_status.csv`: small deterministic index fixture.
- `tests/`: focused pytest suite for each module.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/gupiaofenxi/__init__.py`
- Modify: `README.md`
- Test: `tests/test_project_import.py`

- [ ] **Step 1: Write the failing import test**

Create `tests/test_project_import.py`:

```python
def test_package_imports():
    import gupiaofenxi

    assert gupiaofenxi.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_project_import.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'gupiaofenxi'`.

- [ ] **Step 3: Add package scaffold**

Create `pyproject.toml`:

```toml
[project]
name = "gupiaofenxi"
version = "0.1.0"
description = "Local A-share short-term dip-buying analysis dashboard"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "jinja2>=3.1",
  "pandas>=2.2",
  "pydantic>=2.7",
  "uvicorn>=0.29",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Create `src/gupiaofenxi/__init__.py`:

```python
__version__ = "0.1.0"
```

Replace `README.md`:

```markdown
# gupiaofenxi

A local A-share short-term dip-buying analysis dashboard.

First version goals:

- Generate a recent-strong-stock pool.
- Filter by price, liquidity, ST status, and manual exclusions.
- Rank candidates by score.
- Show data freshness and failure status.
- Produce labels, probabilities, expected return, and trade plans.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_project_import.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/gupiaofenxi/__init__.py tests/test_project_import.py
git commit -m "chore: scaffold python project"
```

## Task 2: Domain Models and Settings

**Files:**
- Create: `src/gupiaofenxi/domain/models.py`
- Create: `src/gupiaofenxi/config.py`
- Test: `tests/test_models_and_config.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_models_and_config.py`:

```python
from datetime import date

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, StockQuote


def test_default_price_range_matches_personal_constraints():
    settings = AppSettings()

    assert settings.min_price == 3
    assert settings.max_price == 60


def test_stock_quote_computes_amplitude():
    quote = StockQuote(
        symbol="000001",
        name="平安银行",
        trade_date=date(2026, 5, 15),
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000000,
        amount=10500000,
        pct_change=3.5,
        is_st=False,
        is_suspended=False,
    )

    assert quote.amplitude == 20
    assert CandidateLabel.STRONG_WATCH.value == "强烈关注"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models_and_config.py -v`

Expected: FAIL because `gupiaofenxi.config` and `gupiaofenxi.domain.models` do not exist.

- [ ] **Step 3: Implement models and settings**

Create `src/gupiaofenxi/domain/models.py`:

```python
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class CandidateLabel(str, Enum):
    STRONG_WATCH = "强烈关注"
    WATCH = "观察"
    REJECT = "放弃"
    HIGH_RISK = "风险过高"
    PRICE_MISMATCH = "价格不合适"
    INSUFFICIENT_DATA = "数据不足"


class DataTaskStatus(str, Enum):
    SUCCESS = "成功"
    FAILED = "失败"
    PARTIAL = "部分成功"


class StockQuote(BaseModel):
    symbol: str
    name: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pct_change: float
    is_st: bool = False
    is_suspended: bool = False
    industry: str | None = None
    concept: str | None = None

    @computed_field
    @property
    def amplitude(self) -> float:
        return round((self.high - self.low) / self.open * 100, 2)


class DataStatusRecord(BaseModel):
    task_name: str
    source_name: str
    status: DataTaskStatus
    started_at: datetime
    ended_at: datetime
    message: str
    success_count: int = 0
    failed_count: int = 0
    missing_count: int = 0
    used_cache: bool = False


class ManualOverride(BaseModel):
    symbol: str
    excluded: bool = False
    focus: bool = False
    note: str = ""


class TradePlan(BaseModel):
    buy_low: float
    buy_high: float
    stop_loss: float
    target_price: float
    trigger: str


class CandidateScore(BaseModel):
    symbol: str
    name: str
    current_price: float
    score: float = Field(ge=0, le=100)
    next_day_up_probability: float = Field(ge=0, le=1)
    three_day_up_probability: float = Field(ge=0, le=1)
    expected_return: float
    label: CandidateLabel
    reason: str
    strength_score: float
    dip_position_score: float
    sentiment_score: float
    historical_similarity_score: float
    trade_plan: TradePlan | None = None


class DashboardReport(BaseModel):
    report_date: date
    generated_at: datetime
    market_temperature: str
    strong_pool_count: int
    high_score_count: int
    risk_count: int
    price_range: tuple[float, float]
    data_status: list[DataStatusRecord]
    candidates: list[CandidateScore]
```

Create `src/gupiaofenxi/config.py`:

```python
from pydantic import BaseModel


class AppSettings(BaseModel):
    min_price: float = 3
    max_price: float = 60
    strong_pool_lookback_days: int = 20
    min_amount: float = 100_000_000
    top_pool_size: int = 300
    high_score_threshold: float = 75
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models_and_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gupiaofenxi/domain/models.py src/gupiaofenxi/config.py tests/test_models_and_config.py
git commit -m "feat: add domain models and settings"
```

## Task 3: Data Status Logging

**Files:**
- Create: `src/gupiaofenxi/data/status.py`
- Test: `tests/test_data_status.py`

- [ ] **Step 1: Write the failing status tests**

Create `tests/test_data_status.py`:

```python
from datetime import datetime

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus


def test_status_log_records_success():
    log = DataStatusLog()

    record = log.record(
        task_name="日线行情",
        source_name="sample",
        status=DataTaskStatus.SUCCESS,
        started_at=datetime(2026, 5, 17, 15, 42),
        ended_at=datetime(2026, 5, 17, 15, 43),
        message="获取成功",
        success_count=286,
    )

    assert record.task_name == "日线行情"
    assert record.success_count == 286
    assert log.latest("日线行情").status == DataTaskStatus.SUCCESS


def test_status_summary_mentions_cache_when_failure_uses_cache():
    log = DataStatusLog()
    log.record(
        task_name="日线行情",
        source_name="sample",
        status=DataTaskStatus.FAILED,
        started_at=datetime(2026, 5, 17, 9, 12),
        ended_at=datetime(2026, 5, 17, 9, 13),
        message="网络错误",
        used_cache=True,
    )

    assert "日线行情获取失败" in log.summary()
    assert "使用缓存" in log.summary()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_data_status.py -v`

Expected: FAIL because `gupiaofenxi.data.status` does not exist.

- [ ] **Step 3: Implement status logger**

Create `src/gupiaofenxi/data/status.py`:

```python
from datetime import datetime

from gupiaofenxi.domain.models import DataStatusRecord, DataTaskStatus


class DataStatusLog:
    def __init__(self, records: list[DataStatusRecord] | None = None):
        self.records = records or []

    def record(
        self,
        task_name: str,
        source_name: str,
        status: DataTaskStatus,
        started_at: datetime,
        ended_at: datetime,
        message: str,
        success_count: int = 0,
        failed_count: int = 0,
        missing_count: int = 0,
        used_cache: bool = False,
    ) -> DataStatusRecord:
        record = DataStatusRecord(
            task_name=task_name,
            source_name=source_name,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            message=message,
            success_count=success_count,
            failed_count=failed_count,
            missing_count=missing_count,
            used_cache=used_cache,
        )
        self.records.append(record)
        return record

    def latest(self, task_name: str) -> DataStatusRecord:
        matches = [record for record in self.records if record.task_name == task_name]
        if not matches:
            raise KeyError(f"No status record for {task_name}")
        return matches[-1]

    def summary(self) -> str:
        if not self.records:
            return "数据状态：暂无数据"
        parts = []
        for record in self.records[-4:]:
            time_text = record.ended_at.strftime("%H:%M")
            if record.status == DataTaskStatus.SUCCESS:
                parts.append(f"{record.task_name}已更新 {time_text}")
            elif record.used_cache:
                parts.append(f"{record.task_name}获取失败 {time_text}，使用缓存")
            else:
                parts.append(f"{record.task_name}获取失败 {time_text}")
        return "数据状态：" + " | ".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_data_status.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gupiaofenxi/data/status.py tests/test_data_status.py
git commit -m "feat: add data status logging"
```

## Task 4: Sample Data Provider

**Files:**
- Create: `data/sample/daily_quotes.csv`
- Create: `data/sample/index_status.csv`
- Create: `src/gupiaofenxi/data/sample_provider.py`
- Test: `tests/test_sample_provider.py`

- [ ] **Step 1: Write the failing provider tests**

Create `tests/test_sample_provider.py`:

```python
from pathlib import Path

from gupiaofenxi.data.sample_provider import SampleDataProvider


def test_sample_provider_loads_quotes_and_records_status():
    provider = SampleDataProvider(Path("data/sample"))

    quotes, status_log = provider.load_daily_quotes()

    assert len(quotes) == 6
    assert quotes[0].symbol == "000001"
    assert status_log.latest("日线行情").success_count == 6


def test_sample_provider_loads_market_temperature():
    provider = SampleDataProvider(Path("data/sample"))

    temperature, status_log = provider.load_market_temperature()

    assert temperature == "偏强"
    assert status_log.latest("指数数据").message == "获取成功"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_provider.py -v`

Expected: FAIL because sample files and provider do not exist.

- [ ] **Step 3: Add deterministic fixture data**

Create `data/sample/daily_quotes.csv`:

```csv
symbol,name,trade_date,open,high,low,close,volume,amount,pct_change,is_st,is_suspended,industry,concept,twenty_day_return,five_day_return,volume_ratio
000001,平安银行,2026-05-15,10.00,10.80,9.80,10.50,1000000,120000000,4.20,false,false,银行,权重,18.5,-3.0,1.20
002001,新和成,2026-05-15,24.00,25.30,23.20,24.50,900000,180000000,2.10,false,false,医药,合成生物,32.0,-6.5,0.82
300001,特锐德,2026-05-15,18.00,18.60,16.80,17.20,1100000,150000000,-3.90,false,false,电力设备,充电桩,41.0,-9.0,0.74
600001,邯郸钢铁,2026-05-15,2.20,2.30,2.10,2.22,500000,9000000,1.00,false,false,钢铁,低价股,22.0,-4.0,1.00
600519,贵州茅台,2026-05-15,1500.00,1518.00,1488.00,1508.00,80000,300000000,0.60,false,false,白酒,消费,16.0,-2.0,0.95
000002,万科A,2026-05-15,8.80,8.95,8.30,8.40,1300000,130000000,-4.50,false,false,房地产,地产链,35.0,-12.0,1.35
```

Create `data/sample/index_status.csv`:

```csv
trade_date,market_temperature,up_count,down_count,limit_up_count,limit_down_count
2026-05-15,偏强,3200,1900,82,12
```

- [ ] **Step 4: Implement sample provider**

Create `src/gupiaofenxi/data/sample_provider.py`:

```python
from datetime import datetime
from pathlib import Path

import pandas as pd

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus, StockQuote


class SampleDataProvider:
    def __init__(self, sample_dir: Path):
        self.sample_dir = sample_dir

    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        started_at = datetime.now()
        path = self.sample_dir / "daily_quotes.csv"
        frame = pd.read_csv(path)
        quotes = [
            StockQuote(
                symbol=str(row.symbol).zfill(6),
                name=row.name,
                trade_date=row.trade_date,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                amount=float(row.amount),
                pct_change=float(row.pct_change),
                is_st=bool(row.is_st),
                is_suspended=bool(row.is_suspended),
                industry=row.industry,
                concept=row.concept,
            )
            for row in frame.itertuples(index=False)
        ]
        log = DataStatusLog()
        log.record(
            task_name="日线行情",
            source_name="sample",
            status=DataTaskStatus.SUCCESS,
            started_at=started_at,
            ended_at=datetime.now(),
            message="获取成功",
            success_count=len(quotes),
        )
        return quotes, log

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        started_at = datetime.now()
        path = self.sample_dir / "index_status.csv"
        frame = pd.read_csv(path)
        temperature = str(frame.iloc[0]["market_temperature"])
        log = DataStatusLog()
        log.record(
            task_name="指数数据",
            source_name="sample",
            status=DataTaskStatus.SUCCESS,
            started_at=started_at,
            ended_at=datetime.now(),
            message="获取成功",
            success_count=1,
        )
        return temperature, log
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_provider.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add data/sample src/gupiaofenxi/data/sample_provider.py tests/test_sample_provider.py
git commit -m "feat: add sample market data provider"
```

## Task 5: Strong Pool and Price Filters

**Files:**
- Create: `src/gupiaofenxi/pipeline/strong_pool.py`
- Test: `tests/test_strong_pool.py`

- [ ] **Step 1: Write the failing pool tests**

Create `tests/test_strong_pool.py`:

```python
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.pipeline.strong_pool import build_strong_pool


def test_strong_pool_excludes_prices_outside_range():
    quotes, _ = SampleDataProvider(Path("data/sample")).load_daily_quotes()

    pool = build_strong_pool(quotes, AppSettings(min_price=3, max_price=60), manual_exclusions=set())
    symbols = {item.symbol for item in pool}

    assert "600519" not in symbols
    assert "600001" not in symbols
    assert "002001" in symbols


def test_strong_pool_honors_manual_exclusions():
    quotes, _ = SampleDataProvider(Path("data/sample")).load_daily_quotes()

    pool = build_strong_pool(quotes, AppSettings(), manual_exclusions={"002001"})
    symbols = {item.symbol for item in pool}

    assert "002001" not in symbols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_strong_pool.py -v`

Expected: FAIL because `build_strong_pool` does not exist.

- [ ] **Step 3: Implement pool filtering**

Create `src/gupiaofenxi/pipeline/strong_pool.py`:

```python
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

    return sorted(filtered, key=lambda quote: (quote.amount, quote.pct_change), reverse=True)[
        : settings.top_pool_size
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_strong_pool.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gupiaofenxi/pipeline/strong_pool.py tests/test_strong_pool.py
git commit -m "feat: add strong pool filters"
```

## Task 6: Scoring and Trade Plans

**Files:**
- Create: `src/gupiaofenxi/pipeline/trade_plan.py`
- Create: `src/gupiaofenxi/pipeline/scoring.py`
- Test: `tests/test_scoring_and_trade_plan.py`

- [ ] **Step 1: Write the failing scoring tests**

Create `tests/test_scoring_and_trade_plan.py`:

```python
from datetime import date

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, StockQuote
from gupiaofenxi.pipeline.scoring import score_candidate


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
    assert 0 <= candidate.score <= 100
    assert 0 <= candidate.next_day_up_probability <= 1
    assert 0 <= candidate.three_day_up_probability <= 1
    assert candidate.trade_plan is not None
    assert candidate.trade_plan.stop_loss < candidate.trade_plan.buy_low


def test_score_candidate_marks_price_mismatch():
    candidate = score_candidate(make_quote(close=88), AppSettings(min_price=3, max_price=60))

    assert candidate.label == CandidateLabel.PRICE_MISMATCH
    assert candidate.trade_plan is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scoring_and_trade_plan.py -v`

Expected: FAIL because scoring and trade plan modules do not exist.

- [ ] **Step 3: Implement trade plan generation**

Create `src/gupiaofenxi/pipeline/trade_plan.py`:

```python
from gupiaofenxi.domain.models import StockQuote, TradePlan


def build_trade_plan(quote: StockQuote) -> TradePlan:
    buy_low = round(quote.close * 0.97, 2)
    buy_high = round(quote.close * 0.995, 2)
    stop_loss = round(buy_low * 0.96, 2)
    target_price = round(quote.close * 1.06, 2)
    return TradePlan(
        buy_low=buy_low,
        buy_high=buy_high,
        stop_loss=stop_loss,
        target_price=target_price,
        trigger="回踩低吸区间且缩量企稳时观察，放量跌破止损位放弃",
    )
```

- [ ] **Step 4: Implement scoring**

Create `src/gupiaofenxi/pipeline/scoring.py`:

```python
from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import CandidateLabel, CandidateScore, StockQuote
from gupiaofenxi.pipeline.trade_plan import build_trade_plan


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_candidate(quote: StockQuote, settings: AppSettings) -> CandidateScore:
    if quote.close < settings.min_price or quote.close > settings.max_price:
        return CandidateScore(
            symbol=quote.symbol,
            name=quote.name,
            current_price=quote.close,
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

    return CandidateScore(
        symbol=quote.symbol,
        name=quote.name,
        current_price=quote.close,
        score=score,
        next_day_up_probability=round(_clamp(0.42 + score / 500, 0, 0.78), 4),
        three_day_up_probability=round(_clamp(0.45 + score / 450, 0, 0.82), 4),
        expected_return=round((score - 50) / 10, 2),
        label=label,
        reason="综合考虑强势基础、回踩位置、成交额和历史相似形态",
        strength_score=round(strength_score, 2),
        dip_position_score=round(dip_position_score, 2),
        sentiment_score=round(sentiment_score, 2),
        historical_similarity_score=round(historical_similarity_score, 2),
        trade_plan=build_trade_plan(quote),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_scoring_and_trade_plan.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gupiaofenxi/pipeline/trade_plan.py src/gupiaofenxi/pipeline/scoring.py tests/test_scoring_and_trade_plan.py
git commit -m "feat: add candidate scoring and trade plans"
```

## Task 7: Report Orchestration

**Files:**
- Create: `src/gupiaofenxi/pipeline/report.py`
- Test: `tests/test_report_pipeline.py`

- [ ] **Step 1: Write the failing report test**

Create `tests/test_report_pipeline.py`:

```python
from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.pipeline.report import build_dashboard_report


def test_build_dashboard_report_contains_status_and_ranked_candidates():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
    )

    assert report.market_temperature == "偏强"
    assert report.strong_pool_count >= 1
    assert len(report.data_status) >= 2
    assert report.candidates == sorted(report.candidates, key=lambda item: item.score, reverse=True)
    assert all(candidate.current_price <= 60 for candidate in report.candidates)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report_pipeline.py -v`

Expected: FAIL because `build_dashboard_report` does not exist.

- [ ] **Step 3: Implement report pipeline**

Create `src/gupiaofenxi/pipeline/report.py`:

```python
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
) -> DashboardReport:
    provider = SampleDataProvider(sample_dir)
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
    report_date = max(quote.trade_date for quote in quotes)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_report_pipeline.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gupiaofenxi/pipeline/report.py tests/test_report_pipeline.py
git commit -m "feat: build dashboard report pipeline"
```

## Task 8: JSON Storage for Reports and Manual Overrides

**Files:**
- Create: `src/gupiaofenxi/storage/json_store.py`
- Test: `tests/test_json_store.py`

- [ ] **Step 1: Write the failing storage test**

Create `tests/test_json_store.py`:

```python
from pathlib import Path

from gupiaofenxi.domain.models import ManualOverride
from gupiaofenxi.storage.json_store import JsonStore


def test_json_store_persists_manual_overrides(tmp_path: Path):
    store = JsonStore(tmp_path)
    store.save_manual_overrides([
        ManualOverride(symbol="002001", excluded=True, note="不做"),
        ManualOverride(symbol="300001", focus=True, note="明天复查"),
    ])

    loaded = store.load_manual_overrides()

    assert loaded["002001"].excluded is True
    assert loaded["300001"].focus is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_json_store.py -v`

Expected: FAIL because `JsonStore` does not exist.

- [ ] **Step 3: Implement JSON storage**

Create `src/gupiaofenxi/storage/json_store.py`:

```python
import json
from pathlib import Path

from gupiaofenxi.domain.models import DashboardReport, ManualOverride


class JsonStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def manual_overrides_path(self) -> Path:
        return self.root / "manual_overrides.json"

    def save_manual_overrides(self, overrides: list[ManualOverride]) -> None:
        payload = [override.model_dump() for override in overrides]
        self.manual_overrides_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_manual_overrides(self) -> dict[str, ManualOverride]:
        if not self.manual_overrides_path.exists():
            return {}
        payload = json.loads(self.manual_overrides_path.read_text(encoding="utf-8"))
        return {item["symbol"]: ManualOverride(**item) for item in payload}

    def save_report(self, report: DashboardReport) -> Path:
        path = self.root / f"report-{report.report_date.isoformat()}.json"
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_json_store.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gupiaofenxi/storage/json_store.py tests/test_json_store.py
git commit -m "feat: persist reports and manual overrides"
```

## Task 9: Local Web Dashboard

**Files:**
- Create: `src/gupiaofenxi/web/app.py`
- Create: `src/gupiaofenxi/web/templates/dashboard.html`
- Create: `src/gupiaofenxi/web/static/styles.css`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Write the failing web test**

Create `tests/test_web_app.py`:

```python
from fastapi.testclient import TestClient

from gupiaofenxi.web.app import create_app


def test_dashboard_page_renders_ranking_first_view():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "A 股短线低吸候选仪表盘" in response.text
    assert "数据状态" in response.text
    assert "当前价" in response.text
    assert "低吸区间" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_web_app.py -v`

Expected: FAIL because `gupiaofenxi.web.app` does not exist.

- [ ] **Step 3: Implement FastAPI app**

Create `src/gupiaofenxi/web/app.py`:

```python
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gupiaofenxi.config import AppSettings
from gupiaofenxi.pipeline.report import build_dashboard_report


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parents[3]


def create_app() -> FastAPI:
    app = FastAPI(title="A 股短线低吸候选仪表盘")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        settings = AppSettings()
        report = build_dashboard_report(
            sample_dir=PROJECT_DIR / "data" / "sample",
            settings=settings,
            manual_exclusions=set(),
        )
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "report": report,
                "settings": settings,
            },
        )

    @app.get("/api/report")
    def api_report():
        return build_dashboard_report(
            sample_dir=PROJECT_DIR / "data" / "sample",
            settings=AppSettings(),
            manual_exclusions=set(),
        )

    return app


app = create_app()
```

- [ ] **Step 4: Implement dashboard template**

Create `src/gupiaofenxi/web/templates/dashboard.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>A 股短线低吸候选仪表盘</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body>
    <main class="page">
      <header class="topbar">
        <div>
          <h1>A 股短线低吸候选仪表盘</h1>
          <p>报告日期 {{ report.report_date }}，生成时间 {{ report.generated_at.strftime("%H:%M:%S") }}</p>
        </div>
        <div class="status-strip">
          数据状态：
          {% for item in report.data_status %}
            <span>{{ item.task_name }} {{ item.status.value }} {{ item.ended_at.strftime("%H:%M") }}</span>
          {% endfor %}
        </div>
      </header>

      <section class="metrics">
        <div><strong>{{ report.market_temperature }}</strong><span>市场温度</span></div>
        <div><strong>{{ report.strong_pool_count }}</strong><span>强势池数量</span></div>
        <div><strong>{{ report.high_score_count }}</strong><span>高分候选</span></div>
        <div><strong>{{ report.risk_count }}</strong><span>风险票</span></div>
        <div><strong>{{ report.price_range[0] }}-{{ report.price_range[1] }}</strong><span>价格范围</span></div>
      </section>

      <section class="filters">
        <label>最低价 <input value="{{ settings.min_price }}"></label>
        <label>最高价 <input value="{{ settings.max_price }}"></label>
        <label>标签 <select><option>全部</option><option>强烈关注</option><option>观察</option></select></label>
        <label>只看强烈关注 <input type="checkbox"></label>
      </section>

      <section class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>当前价</th>
              <th>综合分</th>
              <th>明日概率</th>
              <th>3 日概率</th>
              <th>预期涨幅</th>
              <th>标签</th>
              <th>低吸区间</th>
              <th>止损</th>
              <th>目标</th>
              <th>触发条件</th>
            </tr>
          </thead>
          <tbody>
            {% for item in report.candidates %}
              <tr>
                <td>{{ item.symbol }}</td>
                <td>{{ item.name }}</td>
                <td>{{ "%.2f"|format(item.current_price) }}</td>
                <td>{{ "%.2f"|format(item.score) }}</td>
                <td>{{ "%.1f"|format(item.next_day_up_probability * 100) }}%</td>
                <td>{{ "%.1f"|format(item.three_day_up_probability * 100) }}%</td>
                <td>{{ "%.2f"|format(item.expected_return) }}%</td>
                <td>{{ item.label.value }}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.buy_low }}-{{ item.trade_plan.buy_high }}{% else %}-{% endif %}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.stop_loss }}{% else %}-{% endif %}</td>
                <td>{% if item.trade_plan %}{{ item.trade_plan.target_price }}{% else %}-{% endif %}</td>
                <td>{{ item.trade_plan.trigger if item.trade_plan else item.reason }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
```

- [ ] **Step 5: Implement styling**

Create `src/gupiaofenxi/web/static/styles.css`:

```css
body {
  margin: 0;
  font-family: Arial, "Microsoft YaHei", sans-serif;
  background: #f6f7f9;
  color: #1f2937;
}

.page {
  padding: 20px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}

h1 {
  margin: 0 0 6px;
  font-size: 24px;
}

.status-strip {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  padding: 10px;
  max-width: 620px;
}

.status-strip span {
  display: inline-block;
  margin-right: 10px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 10px;
  margin: 18px 0;
}

.metrics div,
.filters,
.table-wrap {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 6px;
}

.metrics div {
  padding: 12px;
}

.metrics strong {
  display: block;
  font-size: 22px;
}

.metrics span {
  color: #6b7280;
  font-size: 13px;
}

.filters {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px;
  margin-bottom: 14px;
}

.filters input,
.filters select {
  margin-left: 6px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  width: 100%;
  min-width: 1180px;
}

th,
td {
  border-bottom: 1px solid #e5e7eb;
  padding: 9px 10px;
  text-align: left;
  font-size: 14px;
  white-space: nowrap;
}

th {
  background: #eef2f7;
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_web_app.py -v`

Expected: PASS.

- [ ] **Step 7: Manually run the app**

Run: `python -m uvicorn gupiaofenxi.web.app:app --reload --app-dir src`

Expected: Local dashboard opens at `http://127.0.0.1:8000` and shows ranking table plus data status.

- [ ] **Step 8: Commit**

```bash
git add src/gupiaofenxi/web tests/test_web_app.py
git commit -m "feat: add local dashboard web app"
```

## Task 10: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Test: full test suite and local app smoke test.

- [ ] **Step 1: Update README with exact setup and run commands**

Replace `README.md`:

```markdown
# gupiaofenxi

本地 A 股短线低吸候选仪表盘。

## 第一版能力

- 从近期强势股池中筛选低吸候选。
- 支持价格区间过滤，默认 3-60 元。
- 输出综合分、明日上涨概率、3 日上涨概率、预期涨幅和标签。
- 输出低吸区间、止损位、目标位和触发条件。
- 顶部展示数据状态，包括最后获取时间、成功/失败状态和缓存提示。

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 运行测试

```powershell
python -m pytest -v
```

## 启动本地仪表盘

```powershell
python -m uvicorn gupiaofenxi.web.app:app --reload --app-dir src
```

打开：

```text
http://127.0.0.1:8000
```

## 说明

当前版本使用 `data/sample` 下的样例行情数据，先保证评分、筛选、数据状态和页面结构可用。后续再接入 AkShare、Tushare 或 CSV 导入。

概率和预期涨幅是基于规则与历史相似思想的模型估计，不是确定性预测。
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -v`

Expected: all tests PASS.

- [ ] **Step 3: Start the app for smoke verification**

Run: `python -m uvicorn gupiaofenxi.web.app:app --reload --app-dir src`

Expected: server starts with `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 4: Open the dashboard**

Open `http://127.0.0.1:8000`.

Expected:

- Page title is `A 股短线低吸候选仪表盘`.
- Top bar shows `数据状态`.
- Metrics show market temperature, strong pool count, high-score count, risk count, and price range.
- Table includes `当前价`, `综合分`, `明日概率`, `3 日概率`, `低吸区间`, `止损`, and `目标`.
- `600519` and `600001` are absent because their prices are outside the default 3-60 yuan range.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add local dashboard setup instructions"
```

- [ ] **Step 6: Push**

```bash
git push origin main
```

Expected: GitHub `main` receives all implementation commits.

## Self-Review

Spec coverage:

- Ranking-first local web dashboard: covered by Task 9.
- Data status visibility and failure/cache messaging: covered by Task 3, Task 7, and Task 9.
- Price filtering: covered by Task 2 and Task 5.
- Recent strong stock pool: covered by Task 5.
- Score, probabilities, expected return, labels: covered by Task 6.
- Low-buy range, stop loss, target, trigger: covered by Task 6.
- Manual overrides storage: covered by Task 8.
- First-version scope avoids auto trading, intraday alerts, and full backtesting: preserved by file structure and tasks.

Placeholder scan:

- The plan contains no unresolved placeholders or unspecified implementation steps.
- Each code-producing step includes concrete file content.

Type consistency:

- `CandidateLabel`, `StockQuote`, `TradePlan`, `CandidateScore`, and `DashboardReport` are defined in Task 2 and reused consistently in later tasks.
- `AppSettings` fields used in later tasks are defined in Task 2.
- `build_dashboard_report` return type matches the web and storage consumers.
