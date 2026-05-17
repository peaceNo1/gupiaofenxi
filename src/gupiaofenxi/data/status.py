from datetime import datetime

from gupiaofenxi.domain.models import DataStatusRecord, DataTaskStatus


class DataStatusLog:
    def __init__(self, records: list[DataStatusRecord] | None = None):
        self.records = list(records or [])

    def record(
        self,
        task_name: str,
        source_name: str,
        status: DataTaskStatus,
        started_at: datetime,
        ended_at: datetime,
        message: str,
        success_count: int = 0,
        failed_count: int = 0,
        missing_count: int = 0,
        used_cache: bool = False,
    ) -> DataStatusRecord:
        record = DataStatusRecord(
            task_name=task_name,
            source_name=source_name,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            message=message,
            success_count=success_count,
            failed_count=failed_count,
            missing_count=missing_count,
            used_cache=used_cache,
        )
        self.records.append(record)
        return record

    def latest(self, task_name: str) -> DataStatusRecord:
        matches = [record for record in self.records if record.task_name == task_name]
        if not matches:
            raise KeyError(f"No status record for {task_name}")
        return matches[-1]

    def summary(self) -> str:
        if not self.records:
            return "数据状态：暂无数据"
        parts = []
        for record in self.records[-4:]:
            time_text = record.ended_at.strftime("%H:%M")
            if record.status == DataTaskStatus.SUCCESS:
                parts.append(f"{record.task_name}已更新 {time_text}")
            elif record.status == DataTaskStatus.PARTIAL:
                text = f"{record.task_name}部分成功 {time_text}"
                if record.used_cache:
                    text += "，使用缓存"
                parts.append(text)
            elif record.used_cache:
                parts.append(f"{record.task_name}获取失败 {time_text}，使用缓存")
            else:
                parts.append(f"{record.task_name}获取失败 {time_text}")
        return "数据状态：" + " | ".join(parts)
