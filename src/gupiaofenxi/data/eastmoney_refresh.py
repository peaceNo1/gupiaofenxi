import csv
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


EASTMONEY_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_FIELDS = "f12,f14,f2,f17,f15,f16,f5,f6,f3"
EASTMONEY_MARKETS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"


class EastmoneyRefreshError(RuntimeError):
    pass


class EastmoneyRefresher:
    def __init__(self, csv_path: Path, timeout_seconds: float = 12):
        self.csv_path = csv_path
        self.timeout_seconds = timeout_seconds

    def refresh(self) -> int:
        rows = self._fetch_rows()
        if not rows:
            raise EastmoneyRefreshError("东方财富返回空行情")
        self._write_csv(rows)
        return len(rows)

    def _fetch_rows(self) -> list[dict[str, Any]]:
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            EASTMONEY_URL,
            params={
                "pn": 1,
                "pz": 6000,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": EASTMONEY_MARKETS,
                "fields": EASTMONEY_FIELDS,
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", {}).get("diff", [])
        if not isinstance(rows, list):
            raise EastmoneyRefreshError("东方财富响应格式异常")
        return rows

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
