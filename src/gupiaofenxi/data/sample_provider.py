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
        frame = pd.read_csv(
            path,
            dtype={"symbol": str},
            true_values=["true"],
            false_values=["false"],
        )
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
