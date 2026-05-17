from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import date, datetime
from typing import Any

import pandas as pd

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus, StockQuote

COL_SYMBOL = "\u4ee3\u7801"
COL_NAME = "\u540d\u79f0"
COL_CLOSE = "\u6700\u65b0\u4ef7"
COL_OPEN = "\u4eca\u5f00"
COL_HIGH = "\u6700\u9ad8"
COL_LOW = "\u6700\u4f4e"
COL_VOLUME = "\u6210\u4ea4\u91cf"
COL_AMOUNT = "\u6210\u4ea4\u989d"
COL_PCT_CHANGE = "\u6da8\u8dcc\u5e45"


def _first_present(row: pd.Series, names: list[str], default: Any = None) -> Any:
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def _to_float(value: Any) -> float:
    if value in (None, "", "-"):
        raise ValueError("missing numeric value")
    return float(value)


def _fetch_stock_zh_a_spot_em() -> pd.DataFrame:
    import akshare as ak

    return ak.stock_zh_a_spot_em()


class AkshareDataProvider:
    source_name = "akshare.stock_zh_a_spot_em"

    def __init__(self, timeout_seconds: float = 10):
        self.timeout_seconds = timeout_seconds
        self._spot_frame: pd.DataFrame | None = None
        self._spot_error: Exception | None = None

    def _load_spot_frame(self) -> pd.DataFrame:
        if self._spot_frame is not None:
            return self._spot_frame.copy()
        if self._spot_error is not None:
            raise RuntimeError(f"AkShare previous fetch failed: {self._spot_error}")

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_fetch_stock_zh_a_spot_em)
        try:
            self._spot_frame = future.result(timeout=self.timeout_seconds)
            return self._spot_frame.copy()
        except FutureTimeoutError as exc:
            self._spot_error = TimeoutError(f"AkShare fetch timed out after {self.timeout_seconds}s")
            raise self._spot_error from exc
        except Exception as exc:
            self._spot_error = exc
            raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def load_daily_quotes(self) -> tuple[list[StockQuote], DataStatusLog]:
        started_at = datetime.now()
        log = DataStatusLog()
        frame = self._load_spot_frame()
        quotes: list[StockQuote] = []
        missing_count = 0

        for _, row in frame.iterrows():
            try:
                symbol = str(_first_present(row, [COL_SYMBOL, "symbol", "code"])).zfill(6)
                name = str(_first_present(row, [COL_NAME, "name"]))
                close = _to_float(_first_present(row, [COL_CLOSE, "close"]))
                open_price = _to_float(_first_present(row, [COL_OPEN, "open"]))
                high = _to_float(_first_present(row, [COL_HIGH, "high"]))
                low = _to_float(_first_present(row, [COL_LOW, "low"]))
                volume = _to_float(_first_present(row, [COL_VOLUME, "volume"], 0))
                amount = _to_float(_first_present(row, [COL_AMOUNT, "amount"], 0))
                pct_change = _to_float(_first_present(row, [COL_PCT_CHANGE, "pct_change"], 0))
                quotes.append(
                    StockQuote(
                        symbol=symbol,
                        name=name,
                        trade_date=date.today(),
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        amount=amount,
                        pct_change=pct_change,
                        is_st="ST" in name.upper(),
                        is_suspended=False,
                    )
                )
            except (TypeError, ValueError):
                missing_count += 1

        status = DataTaskStatus.SUCCESS if missing_count == 0 else DataTaskStatus.PARTIAL
        log.record(
            task_name="\u5b9e\u65f6\u884c\u60c5",
            source_name=self.source_name,
            status=status,
            started_at=started_at,
            ended_at=datetime.now(),
            message="\u83b7\u53d6\u6210\u529f"
            if status == DataTaskStatus.SUCCESS
            else "\u90e8\u5206\u80a1\u7968\u6570\u636e\u7f3a\u5931",
            success_count=len(quotes),
            missing_count=missing_count,
        )
        return quotes, log

    def load_market_temperature(self) -> tuple[str, DataStatusLog]:
        started_at = datetime.now()
        log = DataStatusLog()
        frame = self._load_spot_frame()
        pct_column = COL_PCT_CHANGE if COL_PCT_CHANGE in frame.columns else "pct_change"
        changes = pd.to_numeric(frame[pct_column], errors="coerce").dropna()
        if changes.empty:
            temperature = "\u672a\u77e5"
        else:
            up_ratio = float((changes > 0).mean())
            if up_ratio >= 0.55:
                temperature = "\u504f\u5f3a"
            elif up_ratio <= 0.45:
                temperature = "\u504f\u5f31"
            else:
                temperature = "\u9707\u8361"
        log.record(
            task_name="\u5e02\u573a\u6e29\u5ea6",
            source_name=self.source_name,
            status=DataTaskStatus.SUCCESS,
            started_at=started_at,
            ended_at=datetime.now(),
            message="\u83b7\u53d6\u6210\u529f",
            success_count=len(changes),
        )
        return temperature, log
