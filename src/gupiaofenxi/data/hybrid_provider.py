from datetime import datetime

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus, StockQuote


class HybridDataProvider:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        started_at = datetime.now()
        try:
            return self.primary.load_daily_quotes()
        except Exception as exc:
            quotes, fallback_log = self.fallback.load_daily_quotes()
            failure_log = DataStatusLog()
            failure_log.record(
                task_name="实时行情",
                source_name=getattr(self.primary, "source_name", self.primary.__class__.__name__),
                status=DataTaskStatus.FAILED,
                started_at=started_at,
                ended_at=datetime.now(),
                message=f"获取失败：{exc}",
                used_cache=True,
            )
            return quotes, DataStatusLog([*failure_log.records, *fallback_log.records])

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        started_at = datetime.now()
        try:
            return self.primary.load_market_temperature()
        except Exception as exc:
            temperature, fallback_log = self.fallback.load_market_temperature()
            failure_log = DataStatusLog()
            failure_log.record(
                task_name="市场温度",
                source_name=getattr(self.primary, "source_name", self.primary.__class__.__name__),
                status=DataTaskStatus.FAILED,
                started_at=started_at,
                ended_at=datetime.now(),
                message=f"获取失败：{exc}",
                used_cache=True,
            )
            return temperature, DataStatusLog([*failure_log.records, *fallback_log.records])
