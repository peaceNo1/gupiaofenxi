from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.pipeline.report import build_dashboard_report


def test_build_dashboard_report_contains_status_and_ranked_candidates():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
    )

    assert report.market_temperature == "偏强"
    assert report.strong_pool_count >= 1
    assert len(report.data_status) >= 2
    assert report.candidates == sorted(report.candidates, key=lambda item: item.score, reverse=True)
    assert all(candidate.current_price <= 60 for candidate in report.candidates)


def test_build_dashboard_report_handles_empty_daily_quotes(tmp_path):
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    daily_quote_header = (
        "symbol,name,trade_date,open,high,low,close,volume,amount,pct_change,"
        "is_st,is_suspended,industry,concept,twenty_day_return,five_day_return,volume_ratio\n"
    )
    (sample_dir / "daily_quotes.csv").write_text(daily_quote_header, encoding="utf-8")
    (sample_dir / "index_status.csv").write_text(
        "trade_date,market_temperature,up_count,down_count,limit_up_count,limit_down_count\n"
        "2026-05-15,stable,3200,1900,82,12\n",
        encoding="utf-8",
    )

    report = build_dashboard_report(
        sample_dir=sample_dir,
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
    )

    assert report.strong_pool_count == 0
    assert report.high_score_count == 0
    assert report.risk_count == 0
    assert report.market_temperature == "stable"
    assert len(report.data_status) >= 2
    assert report.candidates == []
