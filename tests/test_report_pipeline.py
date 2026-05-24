from pathlib import Path

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import Position
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


def test_build_dashboard_report_filters_by_symbol_and_name_and_marks_favorites():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
        favorite_symbols={"000001"},
        symbol_query="000",
        name_query="银行",
    )

    assert [item.symbol for item in report.candidates] == ["000001"]
    assert report.candidates[0].is_favorite is True
    assert [item.symbol for item in report.favorite_candidates] == ["000001"]


def test_build_dashboard_report_searches_before_top_pool_truncation():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60, top_pool_size=1),
        manual_exclusions=set(),
        symbol_query="000001",
    )

    assert [item.symbol for item in report.candidates] == ["000001"]


def test_build_dashboard_report_uses_historical_prediction_samples():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
        prediction_samples=[
            {"score": 64, "next_day_return": 1.2, "three_day_return": 2.0},
            {"score": 63, "next_day_return": -0.4, "three_day_return": 1.0},
        ],
        prediction_min_samples=2,
    )

    assert report.candidates[0].expected_return in {1.5, 2.0, 1.0}
    assert "历史相似样本" in report.candidates[0].reason


def test_build_dashboard_report_calculates_positions_and_alerts():
    report = build_dashboard_report(
        sample_dir=Path("data/sample"),
        settings=AppSettings(min_price=3, max_price=60),
        manual_exclusions=set(),
        favorite_symbols={"000001"},
        positions=[
            Position(symbol="000001", name="平安银行", cost_price=9.6, quantity=1000),
        ],
    )

    position = report.positions[0]
    assert position.symbol == "000001"
    assert position.market_value == 10500
    assert position.profit == 900
    assert position.profit_pct == 9.38
    assert position.status == "止盈"
    assert report.alerts


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
