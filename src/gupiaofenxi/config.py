from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    min_price: float = Field(default=3, gt=0)
    max_price: float = Field(default=60, gt=0)
    strong_pool_lookback_days: int = Field(default=20, gt=0)
    min_amount: float = Field(default=100_000_000, gt=0)
    top_pool_size: int = Field(default=300, gt=0)
    high_score_threshold: float = Field(default=75, ge=0, le=100)
