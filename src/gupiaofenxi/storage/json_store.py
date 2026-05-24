import json
from pathlib import Path

from gupiaofenxi.domain.models import DashboardReport, ManualOverride, Position


class JsonStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def manual_overrides_path(self) -> Path:
        return self.root / "manual_overrides.json"

    @property
    def positions_path(self) -> Path:
        return self.root / "positions.json"

    def save_manual_overrides(self, overrides: list[ManualOverride]) -> None:
        payload = [override.model_dump() for override in overrides]
        self.manual_overrides_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_manual_overrides(self) -> dict[str, ManualOverride]:
        if not self.manual_overrides_path.exists():
            return {}
        payload = json.loads(self.manual_overrides_path.read_text(encoding="utf-8"))
        return {item["symbol"]: ManualOverride(**item) for item in payload}

    def set_focus(self, symbol: str, focus: bool) -> None:
        symbol = symbol.zfill(6)
        overrides = self.load_manual_overrides()
        current = overrides.get(symbol, ManualOverride(symbol=symbol))
        overrides[symbol] = current.model_copy(update={"focus": focus})
        self.save_manual_overrides(list(overrides.values()))

    def focused_symbols(self) -> set[str]:
        return {
            symbol
            for symbol, override in self.load_manual_overrides().items()
            if override.focus
        }

    def save_positions(self, positions: list[Position]) -> None:
        payload = [position.model_dump() for position in positions]
        self.positions_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_positions(self) -> dict[str, Position]:
        if not self.positions_path.exists():
            return {}
        payload = json.loads(self.positions_path.read_text(encoding="utf-8"))
        return {item["symbol"]: Position(**item) for item in payload}

    def upsert_position(self, position: Position) -> None:
        positions = self.load_positions()
        normalized = position.model_copy(update={"symbol": position.symbol.zfill(6)})
        positions[normalized.symbol] = normalized
        self.save_positions(list(positions.values()))

    def delete_position(self, symbol: str) -> None:
        positions = self.load_positions()
        positions.pop(symbol.zfill(6), None)
        self.save_positions(list(positions.values()))

    def save_report(self, report: DashboardReport) -> Path:
        path = self.root / f"report-{report.report_date.isoformat()}.json"
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path
