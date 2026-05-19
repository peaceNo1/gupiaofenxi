from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class SimilaritySample:
    score: float
    next_day_return: float
    three_day_return: float


@dataclass(frozen=True)
class PredictionEstimate:
    next_day_up_probability: float
    three_day_up_probability: float
    expected_return: float
    sample_count: int
    source: str


class HistoricalPrediction:
    def __init__(
        self,
        samples: list[SimilaritySample],
        min_samples: int = 8,
        score_band: float = 5,
    ):
        self.samples = samples
        self.min_samples = min_samples
        self.score_band = score_band

    def estimate(self, score: float) -> PredictionEstimate:
        matches = [
            sample
            for sample in self.samples
            if abs(sample.score - score) <= self.score_band
        ]
        if len(matches) < self.min_samples:
            return self._fallback(score, len(matches))

        next_up = sum(sample.next_day_return > 0 for sample in matches) / len(matches)
        three_up = sum(sample.three_day_return > 0 for sample in matches) / len(matches)
        expected_return = sum(sample.three_day_return for sample in matches) / len(matches)
        return PredictionEstimate(
            next_day_up_probability=round(next_up, 4),
            three_day_up_probability=round(three_up, 4),
            expected_return=round(expected_return, 2),
            sample_count=len(matches),
            source="history",
        )

    @staticmethod
    def _fallback(score: float, sample_count: int = 0) -> PredictionEstimate:
        expected_return = round((score - 50) / 10, 2)
        next_day = round(max(0, min(0.78, 0.42 + score / 500)), 4)
        three_day = round(max(0, min(0.82, 0.45 + score / 450)), 4)
        return PredictionEstimate(
            next_day_up_probability=next_day,
            three_day_up_probability=three_day,
            expected_return=expected_return,
            sample_count=sample_count,
            source="fallback",
        )


def load_samples_from_reports(root: Path) -> list[SimilaritySample]:
    reports = []
    for path in sorted(root.glob("report-*.json")):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue

    by_symbol: dict[str, list[dict]] = {}
    for report in reports:
        for item in report.get("candidates", []):
            by_symbol.setdefault(item.get("symbol", ""), []).append(item)

    samples: list[SimilaritySample] = []
    for rows in by_symbol.values():
        for index, row in enumerate(rows):
            next_row = rows[index + 1] if index + 1 < len(rows) else None
            three_row = rows[index + 3] if index + 3 < len(rows) else None
            if not next_row:
                continue
            current_price = float(row.get("current_price") or 0)
            if current_price <= 0:
                continue
            next_return = (
                (float(next_row.get("current_price") or 0) - current_price)
                / current_price
                * 100
            )
            if three_row:
                three_return = (
                    (float(three_row.get("current_price") or 0) - current_price)
                    / current_price
                    * 100
                )
            else:
                three_return = next_return
            samples.append(
                SimilaritySample(
                    score=float(row.get("score") or 0),
                    next_day_return=next_return,
                    three_day_return=three_return,
                )
            )
    return samples
