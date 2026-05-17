from datetime import datetime

from gupiaofenxi.data.status import DataStatusLog
from gupiaofenxi.domain.models import DataTaskStatus


def test_status_log_records_success():
    log = DataStatusLog()

    record = log.record(
        task_name="日线行情",
        source_name="sample",
        status=DataTaskStatus.SUCCESS,
        started_at=datetime(2026, 5, 17, 15, 42),
        ended_at=datetime(2026, 5, 17, 15, 43),
        message="获取成功",
        success_count=286,
    )

    assert record.task_name == "日线行情"
    assert record.success_count == 286
    assert log.latest("日线行情").status == DataTaskStatus.SUCCESS


def test_status_summary_mentions_cache_when_failure_uses_cache():
    log = DataStatusLog()
    log.record(
        task_name="日线行情",
        source_name="sample",
        status=DataTaskStatus.FAILED,
        started_at=datetime(2026, 5, 17, 9, 12),
        ended_at=datetime(2026, 5, 17, 9, 13),
        message="网络错误",
        used_cache=True,
    )

    assert "日线行情获取失败" in log.summary()
    assert "使用缓存" in log.summary()
