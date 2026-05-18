from typing import Protocol

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataStatusRecord, StockQuote


class DataProvider(Protocol):
    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        ...

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        ...


class FallbackDataProvider:
    def __init__(self, primary: DataProvider, fallback: DataProvider):
        self.primary = primary
        self.fallback = fallback

    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        quotes, status = self.primary.load_daily_quotes()
        if quotes:
            return quotes, status

        fallback_quotes, fallback_status = self.fallback.load_daily_quotes()
        return fallback_quotes, self._combined_status(status, fallback_status)

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        temperature, status = self.primary.load_market_temperature()
        if temperature != "未知":
            return temperature, status

        fallback_temperature, fallback_status = self.fallback.load_market_temperature()
        return fallback_temperature, self._combined_status(status, fallback_status)

    @staticmethod
    def _combined_status(primary: DataStatusLog, fallback: DataStatusLog) -> DataStatusLog:
        records: list[DataStatusRecord] = []
        records.extend(primary.records)
        records.extend(record.model_copy(update={"used_cache": True}) for record in fallback.records)
        return DataStatusLog(records)
