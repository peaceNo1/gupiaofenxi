import csv
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


EASTMONEY_ENDPOINTS = (
    "https://push2delay.eastmoney.com/api/qt/clist/get",
    "https://push2.eastmoney.com/api/qt/clist/get",
    "https://82.push2.eastmoney.com/api/qt/clist/get",
    "http://push2.eastmoney.com/api/qt/clist/get",
)
EASTMONEY_STOCK_ENDPOINTS = (
    "https://push2delay.eastmoney.com/api/qt/stock/get",
    "https://push2.eastmoney.com/api/qt/stock/get",
)
EASTMONEY_FIELDS = "f12,f14,f2,f17,f15,f16,f5,f6,f3"
EASTMONEY_STOCK_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f170"
EASTMONEY_MARKETS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
EASTMONEY_PAGE_SIZE = 100
EASTMONEY_MAX_PAGES = 80
EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://quote.eastmoney.com/center/gridlist.html",
}


class EastmoneyRefreshError(RuntimeError):
    pass


class EastmoneyRefresher:
    def __init__(
        self,
        csv_path: Path,
        timeout_seconds: float = 12,
        symbols_csv_path: Path | None = None,
    ):
        self.csv_path = csv_path
        self.timeout_seconds = timeout_seconds
        self.symbols_csv_path = symbols_csv_path

    def refresh(self) -> int:
        rows = self._fetch_rows()
        if not rows:
            raise EastmoneyRefreshError("东方财富返回空行情")
        self._write_csv(rows)
        return len(rows)

    def _fetch_rows(self) -> list[dict[str, Any]]:
        session = requests.Session()
        session.trust_env = False
        params = {
            "pz": EASTMONEY_PAGE_SIZE,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": EASTMONEY_MARKETS,
            "fields": EASTMONEY_FIELDS,
        }
        last_error: Exception | None = None
        for endpoint in EASTMONEY_ENDPOINTS:
            all_rows: list[dict[str, Any]] = []
            try:
                for page in range(1, EASTMONEY_MAX_PAGES + 1):
                    response = session.get(
                        endpoint,
                        params={**params, "pn": page},
                        headers=EASTMONEY_HEADERS,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()
                    data = response.json().get("data", {})
                    rows = data.get("diff", [])
                    if not isinstance(rows, list):
                        raise EastmoneyRefreshError("东方财富响应格式异常")
                    if not rows:
                        break
                    all_rows.extend(rows)
                    total = int(data.get("total") or 0)
                    if total and len(all_rows) >= total:
                        break
                    if not total and len(rows) < EASTMONEY_PAGE_SIZE:
                        break
                return all_rows
            except EastmoneyRefreshError:
                raise
            except requests.RequestException as exc:
                last_error = exc

        symbols = self._load_known_symbols()
        if symbols:
            rows = self._fetch_rows_by_symbols(session, symbols)
            if rows:
                return rows

        message = "东方财富连接失败，请稍后重试；当前继续使用已有数据"
        if last_error is not None:
            raise EastmoneyRefreshError(message) from last_error
        raise EastmoneyRefreshError(message)

    def _fetch_rows_by_symbols(
        self, session: requests.Session, symbols: list[str]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            try:
                data = self._fetch_symbol_data(session, symbol)
                if data:
                    rows.append(
                        {
                            "f12": data.get("f57", symbol),
                            "f14": data.get("f58", ""),
                            "f2": self._scaled(data.get("f43")),
                            "f17": self._scaled(data.get("f46")),
                            "f15": self._scaled(data.get("f44")),
                            "f16": self._scaled(data.get("f45")),
                            "f5": data.get("f47", 0),
                            "f6": data.get("f48", 0),
                            "f3": self._scaled(data.get("f170")),
                        }
                    )
            except requests.RequestException:
                continue
        return rows

    def _fetch_symbol_data(self, session: requests.Session, symbol: str) -> dict[str, Any]:
        last_error: requests.RequestException | None = None
        for endpoint in EASTMONEY_STOCK_ENDPOINTS:
            try:
                response = session.get(
                    endpoint,
                    params={
                        "secid": self._to_secid(symbol),
                        "fields": EASTMONEY_STOCK_FIELDS,
                    },
                    headers=EASTMONEY_HEADERS,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json().get("data") or {}
            except requests.RequestException as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        return {}

    def _load_known_symbols(self) -> list[str]:
        symbols: list[str] = []
        seen: set[str] = set()
        for csv_path in [self.csv_path, self.symbols_csv_path]:
            if csv_path is None or not csv_path.exists():
                continue
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    symbol = self._row_symbol(row)
                    if symbol and symbol not in seen:
                        seen.add(symbol)
                        symbols.append(symbol)
        return symbols

    @staticmethod
    def _row_symbol(row: dict[str, str]) -> str:
        for key in ("symbol", "code", "代码", "证券代码"):
            value = row.get(key)
            if value:
                return str(value).strip().zfill(6)
        return ""

    @staticmethod
    def _to_secid(symbol: str) -> str:
        market = "1" if symbol.startswith("6") else "0"
        return f"{market}.{symbol}"

    @staticmethod
    def _scaled(value: Any) -> Any:
        if value in (None, "", "-"):
            return ""
        try:
            return round(float(value) / 100, 4)
        except (TypeError, ValueError):
            return value

    def _write_csv(self, rows: list[dict[str, Any]]) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with self.csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "代码",
                    "名称",
                    "最新价",
                    "今开",
                    "最高",
                    "最低",
                    "成交量",
                    "成交额",
                    "涨跌幅",
                    "刷新时间",
                ],
            )
            writer.writeheader()
            refreshed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for row in rows:
                writer.writerow(
                    {
                        "代码": str(row.get("f12", "")).zfill(6),
                        "名称": row.get("f14", ""),
                        "最新价": row.get("f2", ""),
                        "今开": row.get("f17", row.get("f2", "")),
                        "最高": row.get("f15", row.get("f2", "")),
                        "最低": row.get("f16", row.get("f2", "")),
                        "成交量": row.get("f5", 0),
                        "成交额": row.get("f6", 0),
                        "涨跌幅": row.get("f3", 0),
                        "刷新时间": refreshed_at,
                    }
                )
