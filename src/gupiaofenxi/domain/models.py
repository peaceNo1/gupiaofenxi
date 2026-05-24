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
    open: float = Field(gt=0)
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


class Position(BaseModel):
    symbol: str
    name: str = ""
    cost_price: float = Field(gt=0)
    quantity: int = Field(gt=0)


class PositionSnapshot(BaseModel):
    symbol: str
    name: str
    cost_price: float
    quantity: int
    current_price: float
    market_value: float
    profit: float
    profit_pct: float
    status: str


class AlertItem(BaseModel):
    symbol: str
    name: str
    level: str
    message: str


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
    daily_pct_change: float
    is_favorite: bool = False
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
    favorite_candidates: list[CandidateScore] = []
    positions: list[PositionSnapshot] = []
    alerts: list[AlertItem] = []
