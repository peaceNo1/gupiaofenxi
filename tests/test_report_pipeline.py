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
