from pydantic import BaseModel


class AppSettings(BaseModel):
    min_price: float = 3
    max_price: float = 60
    strong_pool_lookback_days: int = 20
    min_amount: float = 100_000_000
    top_pool_size: int = 300
    high_score_threshold: float = 75
