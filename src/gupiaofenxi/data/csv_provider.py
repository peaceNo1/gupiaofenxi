from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus, StockQuote


ALIASES = {
    "symbol": ["symbol", "code", "代码", "证券代码"],
    "name": ["name", "名称", "证券名称"],
    "trade_date": ["trade_date", "date", "日期", "交易日期"],
    "open": ["open", "今开", "开盘", "开盘价"],
    "high": ["high", "最高", "最高价"],
    "low": ["low", "最低", "最低价"],
    "close": ["close", "最新价", "现价", "当前价", "收盘", "收盘价"],
    "volume": ["volume", "成交量"],
    "amount": ["amount", "成交额"],
    "pct_change": ["pct_change", "涨跌幅", "涨幅"],
    "industry": ["industry", "行业"],
    "concept": ["concept", "概念", "题材"],
}


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = {str(column).strip(): column for column in frame.columns}
    rename: dict[Any, str] = {}
    for target, names in ALIASES.items():
        for name in names:
            if name in normalized:
                rename[normalized[name]] = target
                break
    return frame.rename(columns=rename)


def _cell(row: pd.Series, name: str, default: Any = None) -> Any:
    if name not in row or pd.isna(row[name]) or row[name] == "":
        return default
    return row[name]


def _float_cell(row: pd.Series, name: str, default: float | None = None) -> float:
    value = _cell(row, name, default)
    if value is None:
        raise ValueError(f"missing {name}")
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
    return float(value)


class CsvDataProvider:
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.source_name = f"csv:{csv_path}"

    def _load_frame(self) -> pd.DataFrame:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        return _normalize_columns(pd.read_csv(self.csv_path, dtype=str, encoding="utf-8-sig"))

    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        started_at = datetime.now()
        frame = self._load_frame()
        quotes: list[StockQuote] = []
        missing_count = 0

        for _, row in frame.iterrows():
            try:
                close = _float_cell(row, "close")
                open_price = _float_cell(row, "open", close)
                high = _float_cell(row, "high", close)
                low = _float_cell(row, "low", close)
                trade_date = _cell(row, "trade_date", date.today())
                quotes.append(
                    StockQuote(
                        symbol=str(_cell(row, "symbol")).zfill(6),
                        name=str(_cell(row, "name")),
                        trade_date=trade_date,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=_float_cell(row, "volume", 0),
                        amount=_float_cell(row, "amount", 0),
                        pct_change=_float_cell(row, "pct_change", 0),
                        is_st="ST" in str(_cell(row, "name", "")).upper(),
                        is_suspended=False,
                        industry=_cell(row, "industry"),
                        concept=_cell(row, "concept"),
                    )
                )
            except (TypeError, ValueError):
                missing_count += 1

        status = DataTaskStatus.SUCCESS if missing_count == 0 else DataTaskStatus.PARTIAL
        log = DataStatusLog()
        log.record(
            task_name="CSV导入行情",
            source_name=self.source_name,
            status=status,
            started_at=started_at,
            ended_at=datetime.now(),
            message="获取成功" if status == DataTaskStatus.SUCCESS else "部分股票数据缺失",
            success_count=len(quotes),
            missing_count=missing_count,
        )
        return quotes, log

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        started_at = datetime.now()
        quotes, _ = self.load_daily_quotes()
        if not quotes:
            temperature = "未知"
        else:
            up_ratio = sum(quote.pct_change > 0 for quote in quotes) / len(quotes)
            if up_ratio >= 0.55:
                temperature = "偏强"
            elif up_ratio <= 0.45:
                temperature = "偏弱"
            else:
                temperature = "震荡"
        log = DataStatusLog()
        log.record(
            task_name="CSV市场温度",
            source_name=self.source_name,
            status=DataTaskStatus.SUCCESS,
            started_at=started_at,
            ended_at=datetime.now(),
            message="获取成功",
            success_count=len(quotes),
        )
        return temperature, log
