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


def test_status_summary_reports_partial_without_failure_text():
    log = DataStatusLog()
    log.record(
        task_name="日线行情",
        source_name="sample",
        status=DataTaskStatus.PARTIAL,
        started_at=datetime(2026, 5, 17, 9, 12),
        ended_at=datetime(2026, 5, 17, 9, 13),
        message="部分数据缺失",
        used_cache=True,
    )

    summary = log.summary()

    assert "日线行情部分成功 09:13" in summary
    assert "使用缓存" in summary
    assert "日线行情获取失败" not in summary


def test_status_log_copies_initial_records():
    existing_records = [
        DataStatusLog().record(
            task_name="日线行情",
            source_name="sample",
            status=DataTaskStatus.SUCCESS,
            started_at=datetime(2026, 5, 17, 9, 12),
            ended_at=datetime(2026, 5, 17, 9, 13),
            message="获取成功",
        )
    ]
    log = DataStatusLog(existing_records)

    log.record(
        task_name="实时行情",
        source_name="sample",
        status=DataTaskStatus.SUCCESS,
        started_at=datetime(2026, 5, 17, 9, 14),
        ended_at=datetime(2026, 5, 17, 9, 15),
        message="获取成功",
    )

    assert len(existing_records) == 1
